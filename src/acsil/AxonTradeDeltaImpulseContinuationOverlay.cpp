#include "sierrachart.h"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

SCDLLName("AxonTrade Delta Impulse Continuation Overlay")

namespace
{
const char* kStrategyId = "delta_impulse_continue_10bar_2.5pt_50d";
const int kSignalDrawingBase = 7400000;

struct SignalEvaluation
{
    std::string event_type = "rejected_signal";
    std::string direction = "none";
    std::string action = "reject";
    std::string signal_price;
    std::string stop_price;
    std::string first_target_price;
    std::string runner_target_price;
    std::string invalidation_price;
    std::string rejection_reason = "no_setup";
    std::string notes = "no delta impulse continuation setup";
    double marker_price = 0.0;
    bool should_draw = false;
};

std::string ToStdString(const SCString& value)
{
    return std::string(value.GetChars());
}

int MaxInt(int left, int right)
{
    return left > right ? left : right;
}

int MinInt(int left, int right)
{
    return left < right ? left : right;
}

std::string EscapeCsv(const std::string& value)
{
    const bool needs_quotes = value.find_first_of(",\"\r\n") != std::string::npos;
    if (!needs_quotes)
        return value;

    std::string escaped = "\"";
    for (std::string::const_iterator character = value.begin(); character != value.end(); ++character)
    {
        if (*character == '"')
            escaped += "\"\"";
        else
            escaped += *character;
    }
    escaped += "\"";
    return escaped;
}

std::string FormatNumber(double value)
{
    std::ostringstream output;
    output << std::setprecision(10) << value;
    return output.str();
}

std::string FormatDateKey(const SCDateTime& date_time)
{
    int year = 0;
    int month = 0;
    int day = 0;
    date_time.GetDateYMD(year, month, day);

    std::ostringstream output;
    output << year << '-'
           << std::setw(2) << std::setfill('0') << month << '-'
           << std::setw(2) << std::setfill('0') << day;
    return output.str();
}

bool SameChartDate(const SCDateTime& left, const SCDateTime& right)
{
    return left.GetDate() == right.GetDate();
}

bool FileContainsText(const std::string& file_path, const std::string& text)
{
    std::ifstream input(file_path.c_str());
    if (!input.is_open())
        return false;

    std::string line;
    while (std::getline(input, line))
    {
        if (line.find(text) != std::string::npos)
            return true;
    }

    return false;
}

void AppendSignalLogRowIfMissing(
    const std::string& file_path,
    const std::string& event_key,
    const std::string& event_type,
    const std::string& generated_at,
    const std::string& symbol,
    int chart_number,
    int bar_index,
    const std::string& bar_start_time,
    const std::string& trade_mode,
    const std::string& strategy_id,
    const std::string& signal_id,
    const std::string& direction,
    const std::string& action,
    const std::string& signal_price,
    const std::string& stop_price,
    const std::string& target_price,
    const std::string& invalidation_price,
    const std::string& rejection_reason,
    const std::string& confidence,
    const std::string& notes)
{
    if (FileContainsText(file_path, event_key))
        return;

    const bool file_already_exists = static_cast<bool>(std::ifstream(file_path.c_str()));

    std::ofstream output(file_path.c_str(), std::ios::app);
    if (!output.is_open())
        return;

    if (!file_already_exists)
    {
        output << "schema_version,event_key,event_type,generated_at,symbol,chart_number,"
               << "bar_index,bar_start_time,trade_mode,strategy_id,signal_id,direction,"
               << "action,signal_price,stop_price,target_price,invalidation_price,"
               << "rejection_reason,confidence,notes\n";
    }

    output << 1 << ','
           << EscapeCsv(event_key) << ','
           << EscapeCsv(event_type) << ','
           << EscapeCsv(generated_at) << ','
           << EscapeCsv(symbol) << ','
           << chart_number << ','
           << bar_index << ','
           << EscapeCsv(bar_start_time) << ','
           << EscapeCsv(trade_mode) << ','
           << EscapeCsv(strategy_id) << ','
           << EscapeCsv(signal_id) << ','
           << EscapeCsv(direction) << ','
           << EscapeCsv(action) << ','
           << signal_price << ','
           << stop_price << ','
           << target_price << ','
           << invalidation_price << ','
           << EscapeCsv(rejection_reason) << ','
           << confidence << ','
           << EscapeCsv(notes) << '\n';
}

int LatestClosedBarIndex(SCStudyInterfaceRef sc)
{
    for (int bar_index = sc.ArraySize - 1; bar_index >= 0; --bar_index)
    {
        if (sc.GetBarHasClosedStatus(bar_index) == BHCS_BAR_HAS_CLOSED)
            return bar_index;
    }
    return -1;
}

double BarDelta(SCStudyInterfaceRef sc, int bar_index)
{
    return sc.BaseDataIn[SC_ASKVOL][bar_index] - sc.BaseDataIn[SC_BIDVOL][bar_index];
}

std::vector<int> EligibleLookbackIndices(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    int required_indices)
{
    std::vector<int> indices;
    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];

    for (int index = bar_index; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;

        const int bar_time = sc.BaseDateTimeIn[index].GetTimeInSeconds();
        if (bar_time < setup_start_time)
            break;
        if (bar_time > setup_end_time)
            continue;

        indices.push_back(index);
        if (static_cast<int>(indices.size()) >= required_indices)
            break;
    }

    return indices;
}

SignalEvaluation Rejection(
    double signal_price,
    const std::string& rejection_reason,
    const std::string& notes)
{
    SignalEvaluation evaluation;
    evaluation.signal_price = FormatNumber(signal_price);
    evaluation.rejection_reason = rejection_reason;
    evaluation.notes = notes;
    evaluation.marker_price = signal_price;
    return evaluation;
}

SignalEvaluation EvaluateSignalAtBar(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    int lookback_bars,
    double minimum_price_move_points,
    double minimum_delta_sum,
    int minimum_spacing_seconds,
    int max_signals_per_day,
    double stop_points,
    double first_target_points,
    double runner_target_points)
{
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();

    if (bar_time < setup_start_time || bar_time > setup_end_time)
        return Rejection(close, "outside_session", "bar is outside setup window");
    if (lookback_bars <= 0)
        return Rejection(close, "configuration_error", "lookback bars must be positive");
    if (minimum_price_move_points <= 0.0)
        return Rejection(close, "configuration_error", "minimum price move must be positive");
    if (minimum_delta_sum <= 0.0)
        return Rejection(close, "configuration_error", "minimum delta sum must be positive");
    if (stop_points <= 0.0 || first_target_points <= 0.0 || runner_target_points <= first_target_points)
        return Rejection(close, "configuration_error", "fixed exit points are invalid");

    const std::vector<int> indices = EligibleLookbackIndices(
        sc,
        bar_index,
        setup_start_time,
        setup_end_time,
        lookback_bars + 1);
    if (static_cast<int>(indices.size()) < lookback_bars + 1)
        return Rejection(close, "insufficient_context", "not enough eligible setup-window bars for lookback");

    const int price_reference_index = indices[lookback_bars];
    const double price_move = close - sc.BaseDataIn[SC_LAST][price_reference_index];
    double delta_sum = 0.0;
    for (int offset = 0; offset < lookback_bars; ++offset)
        delta_sum += BarDelta(sc, indices[offset]);

    std::string direction = "none";
    if (price_move >= minimum_price_move_points && delta_sum >= minimum_delta_sum)
        direction = "long";
    else if (price_move <= -minimum_price_move_points && delta_sum <= -minimum_delta_sum)
        direction = "short";
    else
    {
        std::ostringstream notes;
        notes << "price_move=" << FormatNumber(price_move)
              << "; delta_sum=" << FormatNumber(delta_sum)
              << "; thresholds not met";
        return Rejection(close, "no_setup", notes.str());
    }

    SignalEvaluation evaluation;
    evaluation.event_type = "candidate_signal";
    evaluation.direction = direction;
    evaluation.action = "candidate";
    evaluation.signal_price = FormatNumber(close);
    evaluation.rejection_reason = "not_applicable";
    evaluation.marker_price = direction == "long"
        ? sc.BaseDataIn[SC_LOW][bar_index]
        : sc.BaseDataIn[SC_HIGH][bar_index];
    evaluation.should_draw = true;

    const bool is_long = direction == "long";
    const double stop_price = is_long ? close - stop_points : close + stop_points;
    const double first_target_price = is_long ? close + first_target_points : close - first_target_points;
    const double runner_target_price = is_long ? close + runner_target_points : close - runner_target_points;

    evaluation.stop_price = FormatNumber(stop_price);
    evaluation.first_target_price = FormatNumber(first_target_price);
    evaluation.runner_target_price = FormatNumber(runner_target_price);
    evaluation.invalidation_price = evaluation.stop_price;

    std::ostringstream notes;
    notes << direction << " delta impulse continuation; "
          << "lookback_bars=" << lookback_bars << "; "
          << "price_reference_bar_index=" << price_reference_index << "; "
          << "price_move=" << FormatNumber(price_move) << "; "
          << "delta_sum=" << FormatNumber(delta_sum) << "; "
          << "first_target_points=" << FormatNumber(first_target_points) << "; "
          << "runner_target_points=" << FormatNumber(runner_target_points) << "; "
          << "runner_stop_mode=breakeven; "
          << "minimum_spacing_seconds=" << minimum_spacing_seconds << "; "
          << "max_signals_per_day=" << max_signals_per_day;
    evaluation.notes = notes.str();
    return evaluation;
}

std::string SignalId(const std::string& symbol, int bar_index)
{
    std::ostringstream signal_id;
    signal_id << kStrategyId << '_' << symbol << '_' << bar_index;
    return signal_id.str();
}

std::string EventKey(
    const std::string& symbol,
    int chart_number,
    int bar_index,
    const std::string& event_type,
    const std::string& direction)
{
    std::ostringstream event_key;
    event_key << symbol << ':' << chart_number << ':' << bar_index << ':'
              << kStrategyId << ':' << event_type << ':' << direction;
    return event_key.str();
}

void DrawLineSegment(
    SCStudyInterfaceRef sc,
    int drawing_number,
    int bar_index,
    double price,
    COLORREF color,
    int line_width)
{
    s_UseTool tool;
    tool.Clear();
    tool.ChartNumber = sc.ChartNumber;
    tool.DrawingType = DRAWING_LINE;
    tool.LineNumber = drawing_number;
    tool.Region = 0;
    tool.BeginIndex = bar_index;
    tool.EndIndex = MinInt(sc.ArraySize - 1, bar_index + 8);
    tool.BeginValue = price;
    tool.EndValue = price;
    tool.Color = color;
    tool.LineWidth = line_width;
    tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(tool);
}

void DrawCandidateOverlay(
    SCStudyInterfaceRef sc,
    int bar_index,
    const SignalEvaluation& evaluation)
{
    const bool is_long = evaluation.direction == "long";
    const int direction_offset = is_long ? 0 : 100000;
    const int drawing_base = kSignalDrawingBase + direction_offset + bar_index * 10;
    const COLORREF signal_color = is_long ? RGB(0, 180, 255) : RGB(255, 96, 80);
    const double tick_offset = sc.TickSize > 0.0 ? sc.TickSize * 2.0 : 1.0;

    s_UseTool marker;
    marker.Clear();
    marker.ChartNumber = sc.ChartNumber;
    marker.DrawingType = DRAWING_MARKER;
    marker.LineNumber = drawing_base + 1;
    marker.Region = 0;
    marker.BeginIndex = bar_index;
    marker.BeginValue = is_long
        ? evaluation.marker_price - tick_offset
        : evaluation.marker_price + tick_offset;
    marker.MarkerType = is_long ? MARKER_ARROWUP : MARKER_ARROWDOWN;
    marker.MarkerSize = 8;
    marker.LineWidth = 5;
    marker.Color = signal_color;
    marker.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(marker);

    s_UseTool label;
    label.Clear();
    label.ChartNumber = sc.ChartNumber;
    label.DrawingType = DRAWING_TEXT;
    label.LineNumber = drawing_base + 2;
    label.Region = 0;
    label.BeginIndex = bar_index;
    label.BeginValue = marker.BeginValue;
    label.Color = signal_color;
    label.FontSize = 9;
    label.Text = is_long ? "Axon long delta impulse" : "Axon short delta impulse";
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);

    if (!evaluation.stop_price.empty())
        DrawLineSegment(sc, drawing_base + 3, bar_index, std::atof(evaluation.stop_price.c_str()), RGB(220, 64, 64), 1);
    if (!evaluation.first_target_price.empty())
        DrawLineSegment(sc, drawing_base + 4, bar_index, std::atof(evaluation.first_target_price.c_str()), RGB(64, 180, 255), 1);
    if (!evaluation.runner_target_price.empty())
        DrawLineSegment(sc, drawing_base + 5, bar_index, std::atof(evaluation.runner_target_price.c_str()), RGB(64, 220, 120), 2);
}

bool CandidatePacingAllowed(
    SCStudyInterfaceRef sc,
    int bar_index,
    int minimum_spacing_seconds,
    int max_signals_per_day,
    std::string& rejection_reason,
    std::string& notes)
{
    int& signal_date = sc.GetPersistentInt(2);
    int& signal_count = sc.GetPersistentInt(3);
    int& last_signal_time = sc.GetPersistentInt(4);

    const int current_date = sc.BaseDateTimeIn[bar_index].GetDate();
    const int current_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
    if (signal_date != current_date)
    {
        signal_date = current_date;
        signal_count = 0;
        last_signal_time = -1;
    }

    if (max_signals_per_day > 0 && signal_count >= max_signals_per_day)
    {
        rejection_reason = "daily_limit";
        notes = "maximum delta impulse signals reached for this chart date";
        return false;
    }
    if (last_signal_time >= 0 && minimum_spacing_seconds > 0)
    {
        const int seconds_since_last = current_time - last_signal_time;
        if (seconds_since_last >= 0 && seconds_since_last < minimum_spacing_seconds)
        {
            rejection_reason = "spacing_filter";
            std::ostringstream output;
            output << "last delta impulse signal was "
                   << seconds_since_last
                   << " seconds ago, below minimum spacing";
            notes = output.str();
            return false;
        }
    }
    return true;
}

void RecordAcceptedCandidate(SCStudyInterfaceRef sc, int bar_index)
{
    int& signal_date = sc.GetPersistentInt(2);
    int& signal_count = sc.GetPersistentInt(3);
    int& last_signal_time = sc.GetPersistentInt(4);

    signal_date = sc.BaseDateTimeIn[bar_index].GetDate();
    signal_count += 1;
    last_signal_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
}
}

SCSFExport scsf_AxonTradeDeltaImpulseContinuationOverlay(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef TradeMode = sc.Input[1];
    SCInputRef LogRejections = sc.Input[2];
    SCInputRef ProcessFullRecalculation = sc.Input[3];
    SCInputRef SetupStartTime = sc.Input[4];
    SCInputRef SetupEndTime = sc.Input[5];
    SCInputRef LookbackBars = sc.Input[6];
    SCInputRef MinimumPriceMovePoints = sc.Input[7];
    SCInputRef MinimumDeltaSum = sc.Input[8];
    SCInputRef MinimumSpacingSeconds = sc.Input[9];
    SCInputRef MaxSignalsPerDay = sc.Input[10];
    SCInputRef InitialStopPoints = sc.Input[11];
    SCInputRef FirstTargetPoints = sc.Input[12];
    SCInputRef RunnerTargetPoints = sc.Input[13];
    SCInputRef Confidence = sc.Input[14];

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade Delta Impulse Continuation Overlay";
        sc.StudyDescription = "Indicator-only fixed-exit delta impulse continuation overlay and signal-log CSV writer.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_DeltaImpulseSignalLog.csv");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString("replay");

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(1);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(9, 45, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(15, 45, 0));

        LookbackBars.Name = "Lookback Bars";
        LookbackBars.SetInt(10);
        LookbackBars.SetIntLimits(1, 200);

        MinimumPriceMovePoints.Name = "Minimum Price Move Points";
        MinimumPriceMovePoints.SetFloat(2.5f);

        MinimumDeltaSum.Name = "Minimum Delta Sum";
        MinimumDeltaSum.SetFloat(50.0f);

        MinimumSpacingSeconds.Name = "Minimum Signal Spacing Seconds";
        MinimumSpacingSeconds.SetInt(900);
        MinimumSpacingSeconds.SetIntLimits(0, 7200);

        MaxSignalsPerDay.Name = "Max Signals Per Day";
        MaxSignalsPerDay.SetInt(6);
        MaxSignalsPerDay.SetIntLimits(0, 100);

        InitialStopPoints.Name = "Initial Stop Points";
        InitialStopPoints.SetFloat(5.0f);

        FirstTargetPoints.Name = "First Target Points";
        FirstTargetPoints.SetFloat(5.0f);

        RunnerTargetPoints.Name = "Runner Target Points";
        RunnerTargetPoints.SetFloat(15.0f);

        Confidence.Name = "Research Confidence";
        Confidence.SetFloat(0.60f);

        return;
    }

    if (sc.ArraySize <= 1)
        return;

    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    if (csv_log_path.empty())
        return;

    const int latest_closed_bar_index = LatestClosedBarIndex(sc);
    if (latest_closed_bar_index < 0)
        return;

    int& last_processed_bar_index = sc.GetPersistentInt(1);
    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        last_processed_bar_index = -1;
        sc.GetPersistentInt(2) = 0;
        sc.GetPersistentInt(3) = 0;
        sc.GetPersistentInt(4) = -1;
    }
    else if (latest_closed_bar_index < last_processed_bar_index)
    {
        last_processed_bar_index = latest_closed_bar_index - 1;
    }

    int start_bar_index = latest_closed_bar_index;
    if (ProcessFullRecalculation.GetYesNo() != 0 && sc.IsFullRecalculation)
        start_bar_index = 0;
    else if (latest_closed_bar_index <= last_processed_bar_index)
        return;

    const std::string symbol = ToStdString(sc.Symbol);
    const std::string trade_mode = ToStdString(TradeMode.GetString());
    const std::string confidence = FormatNumber(Confidence.GetFloat());

    for (int bar_index = start_bar_index; bar_index <= latest_closed_bar_index; ++bar_index)
    {
        if (bar_index <= last_processed_bar_index)
            continue;
        if (sc.GetBarHasClosedStatus(bar_index) != BHCS_BAR_HAS_CLOSED)
            continue;

        SignalEvaluation evaluation = EvaluateSignalAtBar(
            sc,
            bar_index,
            SetupStartTime.GetTime(),
            SetupEndTime.GetTime(),
            LookbackBars.GetInt(),
            MinimumPriceMovePoints.GetFloat(),
            MinimumDeltaSum.GetFloat(),
            MinimumSpacingSeconds.GetInt(),
            MaxSignalsPerDay.GetInt(),
            InitialStopPoints.GetFloat(),
            FirstTargetPoints.GetFloat(),
            RunnerTargetPoints.GetFloat());

        if (evaluation.event_type == "candidate_signal")
        {
            std::string pacing_rejection_reason;
            std::string pacing_notes;
            if (!CandidatePacingAllowed(
                    sc,
                    bar_index,
                    MinimumSpacingSeconds.GetInt(),
                    MaxSignalsPerDay.GetInt(),
                    pacing_rejection_reason,
                    pacing_notes))
            {
                evaluation = Rejection(
                    sc.BaseDataIn[SC_LAST][bar_index],
                    pacing_rejection_reason,
                    pacing_notes);
            }
            else
            {
                RecordAcceptedCandidate(sc, bar_index);
            }
        }

        const std::string generated_at = ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]));
        const std::string signal_id = SignalId(symbol, bar_index);
        const std::string event_key = EventKey(
            symbol,
            sc.ChartNumber,
            bar_index,
            evaluation.event_type,
            evaluation.direction);

        if (evaluation.event_type == "candidate_signal" || LogRejections.GetYesNo() != 0)
        {
            AppendSignalLogRowIfMissing(
                csv_log_path,
                event_key,
                evaluation.event_type,
                generated_at,
                symbol,
                sc.ChartNumber,
                bar_index,
                generated_at,
                trade_mode,
                kStrategyId,
                signal_id,
                evaluation.direction,
                evaluation.action,
                evaluation.signal_price,
                evaluation.stop_price,
                evaluation.runner_target_price,
                evaluation.invalidation_price,
                evaluation.rejection_reason,
                confidence,
                evaluation.notes);
        }

        if (evaluation.should_draw)
            DrawCandidateOverlay(sc, bar_index, evaluation);

        last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
    }
}
