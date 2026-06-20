#include "sierrachart.h"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>

SCDLLName("AxonTrade Liquidity Sweep Signal Overlay")

namespace
{
const char* kStrategyId = "liquidity_sweep_absorption_reversal";
const int kSignalDrawingBase = 7200000;

struct OpeningRange
{
    bool valid = false;
    double high = 0.0;
    double low = 0.0;
};

struct SweepMatch
{
    bool valid = false;
    int sweep_bar_index = -1;
    double extreme_price = 0.0;
    double delta = 0.0;
    double aggression_ratio = 0.0;
    double close_location = 0.5;
    std::string notes;
};

struct SignalEvaluation
{
    std::string event_type = "rejected_signal";
    std::string direction = "none";
    std::string action = "reject";
    std::string signal_price;
    std::string stop_price;
    std::string target_price;
    std::string invalidation_price;
    std::string rejection_reason = "no_setup";
    std::string notes = "no liquidity sweep reversal setup";
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

double MaxDouble(double left, double right)
{
    return left > right ? left : right;
}

double MinDouble(double left, double right)
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

double CloseLocation(SCStudyInterfaceRef sc, int bar_index)
{
    const double high = sc.BaseDataIn[SC_HIGH][bar_index];
    const double low = sc.BaseDataIn[SC_LOW][bar_index];
    const double range = high - low;
    if (range <= 0.0)
        return 0.5;
    return (sc.BaseDataIn[SC_LAST][bar_index] - low) / range;
}

double SafeRatio(double numerator, double denominator)
{
    if (denominator <= 0.0)
        return numerator > 0.0 ? 999999.0 : 0.0;
    return numerator / denominator;
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

OpeningRange FindOpeningRange(
    SCStudyInterfaceRef sc,
    int bar_index,
    int opening_range_start_time,
    int opening_range_end_time)
{
    OpeningRange result;
    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];

    for (int index = bar_index; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;

        const int bar_time = sc.BaseDateTimeIn[index].GetTimeInSeconds();
        if (bar_time < opening_range_start_time || bar_time > opening_range_end_time)
            continue;

        const double high = sc.BaseDataIn[SC_HIGH][index];
        const double low = sc.BaseDataIn[SC_LOW][index];
        if (!result.valid)
        {
            result.high = high;
            result.low = low;
            result.valid = true;
        }
        else
        {
            result.high = MaxDouble(result.high, high);
            result.low = MinDouble(result.low, low);
        }
    }

    return result;
}

bool SweptDirection(
    SCStudyInterfaceRef sc,
    int bar_index,
    const OpeningRange& opening_range,
    const std::string& direction,
    double minimum_sweep_points)
{
    if (direction == "short")
        return sc.BaseDataIn[SC_HIGH][bar_index] >= opening_range.high + minimum_sweep_points;
    if (direction == "long")
        return sc.BaseDataIn[SC_LOW][bar_index] <= opening_range.low - minimum_sweep_points;
    return false;
}

SweepMatch AbsorptionSweepFromBar(
    SCStudyInterfaceRef sc,
    int bar_index,
    const OpeningRange& opening_range,
    const std::string& direction,
    double minimum_sweep_points,
    double minimum_total_volume,
    double minimum_aggressive_delta,
    double minimum_aggression_ratio)
{
    SweepMatch result;
    if (!SweptDirection(sc, bar_index, opening_range, direction, minimum_sweep_points))
    {
        result.notes = "bar did not sweep the configured opening-range side";
        return result;
    }

    const double bid_volume = sc.BaseDataIn[SC_BIDVOL][bar_index];
    const double ask_volume = sc.BaseDataIn[SC_ASKVOL][bar_index];
    const double chart_volume = sc.BaseDataIn[SC_VOLUME][bar_index];
    const double total_volume = chart_volume > 0.0 ? chart_volume : bid_volume + ask_volume;
    const double delta = ask_volume - bid_volume;
    const double close_location = CloseLocation(sc, bar_index);

    if (total_volume < minimum_total_volume)
    {
        std::ostringstream notes;
        notes << "total volume " << total_volume << " below absorption minimum";
        result.notes = notes.str();
        return result;
    }

    bool delta_ok = false;
    bool ratio_ok = false;
    double aggression_ratio = 0.0;
    double extreme_price = 0.0;
    if (direction == "short")
    {
        aggression_ratio = SafeRatio(ask_volume, bid_volume);
        delta_ok = delta > 0.0 && std::fabs(delta) >= minimum_aggressive_delta;
        ratio_ok = aggression_ratio >= minimum_aggression_ratio;
        extreme_price = sc.BaseDataIn[SC_HIGH][bar_index];
    }
    else
    {
        aggression_ratio = SafeRatio(bid_volume, ask_volume);
        delta_ok = delta < 0.0 && std::fabs(delta) >= minimum_aggressive_delta;
        ratio_ok = aggression_ratio >= minimum_aggression_ratio;
        extreme_price = sc.BaseDataIn[SC_LOW][bar_index];
    }

    std::ostringstream notes;
    notes << direction << " sweep aggression "
          << "delta=" << FormatNumber(delta)
          << "; ratio=" << FormatNumber(aggression_ratio)
          << "; close_location=" << FormatNumber(close_location);

    if (!delta_ok || !ratio_ok)
    {
        notes << "; failed=";
        if (!delta_ok)
            notes << "delta";
        if (!delta_ok && !ratio_ok)
            notes << ",";
        if (!ratio_ok)
            notes << "aggression_ratio";
        result.notes = notes.str();
        return result;
    }

    result.valid = true;
    result.sweep_bar_index = bar_index;
    result.extreme_price = extreme_price;
    result.delta = delta;
    result.aggression_ratio = aggression_ratio;
    result.close_location = close_location;
    result.notes = notes.str();
    return result;
}

bool ConfirmationMatches(
    SCStudyInterfaceRef sc,
    int bar_index,
    const OpeningRange& opening_range,
    const std::string& direction,
    double close_back_inside_points,
    double short_max_close_location,
    double long_min_close_location)
{
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    const double close_location = CloseLocation(sc, bar_index);
    if (direction == "short")
    {
        return close <= opening_range.high - close_back_inside_points
            && close_location <= short_max_close_location;
    }
    if (direction == "long")
    {
        return close >= opening_range.low + close_back_inside_points
            && close_location >= long_min_close_location;
    }
    return false;
}

SweepMatch FindConfirmedSweep(
    SCStudyInterfaceRef sc,
    int bar_index,
    const OpeningRange& opening_range,
    const std::string& direction,
    int setup_start_time,
    int setup_end_time,
    int maximum_reversal_bars,
    double minimum_sweep_points,
    double close_back_inside_points,
    double minimum_total_volume,
    double minimum_aggressive_delta,
    double minimum_aggression_ratio,
    double short_max_close_location,
    double long_min_close_location)
{
    SweepMatch latest_match;
    if (!ConfirmationMatches(
            sc,
            bar_index,
            opening_range,
            direction,
            close_back_inside_points,
            short_max_close_location,
            long_min_close_location))
    {
        return latest_match;
    }

    const int first_index = MaxInt(0, bar_index - maximum_reversal_bars);
    for (int sweep_index = first_index; sweep_index <= bar_index; ++sweep_index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[sweep_index], sc.BaseDateTimeIn[bar_index]))
            continue;

        const int sweep_time = sc.BaseDateTimeIn[sweep_index].GetTimeInSeconds();
        if (sweep_time < setup_start_time || sweep_time > setup_end_time)
            continue;

        const SweepMatch match = AbsorptionSweepFromBar(
            sc,
            sweep_index,
            opening_range,
            direction,
            minimum_sweep_points,
            minimum_total_volume,
            minimum_aggressive_delta,
            minimum_aggression_ratio);
        if (match.valid)
            latest_match = match;
    }

    return latest_match;
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
    int opening_range_start_time,
    int opening_range_end_time,
    int setup_start_time,
    int setup_end_time,
    double minimum_opening_range_width_points,
    double minimum_sweep_points,
    int maximum_reversal_bars,
    double close_back_inside_points,
    double stop_buffer_points,
    double maximum_risk_points,
    double minimum_total_volume,
    double minimum_aggressive_delta,
    double minimum_aggression_ratio,
    double short_max_close_location,
    double long_min_close_location)
{
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
    if (bar_time <= opening_range_end_time)
        return Rejection(close, "insufficient_context", "opening range is not complete");
    if (bar_time < setup_start_time || bar_time > setup_end_time)
        return Rejection(close, "outside_session", "bar is outside setup window");

    const OpeningRange opening_range = FindOpeningRange(
        sc,
        bar_index,
        opening_range_start_time,
        opening_range_end_time);
    if (!opening_range.valid)
        return Rejection(close, "insufficient_context", "opening range bars were not found");

    const double opening_range_width = opening_range.high - opening_range.low;
    if (opening_range_width < minimum_opening_range_width_points)
        return Rejection(close, "insufficient_context", "opening range width is below configured minimum");

    const bool swept_short = SweptDirection(sc, bar_index, opening_range, "short", minimum_sweep_points);
    const bool swept_long = SweptDirection(sc, bar_index, opening_range, "long", minimum_sweep_points);
    if (swept_short && swept_long)
        return Rejection(close, "manual_review_required", "bar swept both opening-range sides");

    for (int direction_index = 0; direction_index < 2; ++direction_index)
    {
        const std::string direction = direction_index == 0 ? "short" : "long";
        const SweepMatch sweep = FindConfirmedSweep(
            sc,
            bar_index,
            opening_range,
            direction,
            setup_start_time,
            setup_end_time,
            maximum_reversal_bars,
            minimum_sweep_points,
            close_back_inside_points,
            minimum_total_volume,
            minimum_aggressive_delta,
            minimum_aggression_ratio,
            short_max_close_location,
            long_min_close_location);
        if (!sweep.valid)
            continue;

        const double target_price = (opening_range.high + opening_range.low) / 2.0;
        const double stop_price = direction == "short"
            ? sweep.extreme_price + stop_buffer_points
            : sweep.extreme_price - stop_buffer_points;
        const double risk_points = direction == "short" ? stop_price - close : close - stop_price;
        const bool target_valid = direction == "short" ? target_price < close : target_price > close;

        if (risk_points <= 0.0)
            return Rejection(close, "risk_limit", "candidate has nonpositive risk distance");
        if (risk_points > maximum_risk_points)
            return Rejection(close, "risk_limit", "candidate risk exceeds configured maximum");
        if (!target_valid)
            return Rejection(close, "risk_limit", "opening-range midpoint target is not beyond entry price");

        SignalEvaluation evaluation;
        evaluation.event_type = "candidate_signal";
        evaluation.direction = direction;
        evaluation.action = "candidate";
        evaluation.signal_price = FormatNumber(close);
        evaluation.stop_price = FormatNumber(stop_price);
        evaluation.target_price = FormatNumber(target_price);
        evaluation.invalidation_price = FormatNumber(stop_price);
        evaluation.rejection_reason = "not_applicable";
        evaluation.marker_price = direction == "short"
            ? sc.BaseDataIn[SC_HIGH][bar_index]
            : sc.BaseDataIn[SC_LOW][bar_index];
        evaluation.should_draw = true;

        std::ostringstream notes;
        notes << direction << " absorption reversal; "
              << "sweep_bar_index=" << sweep.sweep_bar_index << "; "
              << "sweep_delta=" << FormatNumber(sweep.delta) << "; "
              << "sweep_ratio=" << FormatNumber(sweep.aggression_ratio) << "; "
              << "confirmation_close_location=" << FormatNumber(CloseLocation(sc, bar_index));
        evaluation.notes = notes.str();
        return evaluation;
    }

    if (swept_short || swept_long)
    {
        const std::string direction = swept_short ? "short" : "long";
        const SweepMatch sweep = AbsorptionSweepFromBar(
            sc,
            bar_index,
            opening_range,
            direction,
            minimum_sweep_points,
            minimum_total_volume,
            minimum_aggressive_delta,
            minimum_aggression_ratio);
        if (!sweep.valid)
            return Rejection(close, "no_absorption", sweep.notes);
        return Rejection(close, "no_setup", "liquidity sweep observed; waiting for reversal confirmation");
    }

    return Rejection(close, "no_setup", "no liquidity sweep reversal setup");
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

std::string CandidateDaySideKey(
    const std::string& symbol,
    int chart_number,
    const std::string& date_key,
    const std::string& direction)
{
    std::ostringstream key;
    key << symbol << ':' << chart_number << ':' << date_key << ':'
        << direction << ':' << kStrategyId << ":candidate_signal";
    return key.str();
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
    label.Text = is_long ? "Axon long sweep absorption" : "Axon short sweep absorption";
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);

    if (!evaluation.stop_price.empty())
        DrawLineSegment(sc, drawing_base + 3, bar_index, std::atof(evaluation.stop_price.c_str()), RGB(220, 64, 64), 1);
    if (!evaluation.target_price.empty())
        DrawLineSegment(sc, drawing_base + 4, bar_index, std::atof(evaluation.target_price.c_str()), RGB(64, 180, 255), 1);
}
}

SCSFExport scsf_AxonTradeLiquiditySweepSignalOverlay(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef TradeMode = sc.Input[1];
    SCInputRef LogRejections = sc.Input[2];
    SCInputRef ProcessFullRecalculation = sc.Input[3];
    SCInputRef OneSignalPerSidePerDay = sc.Input[4];
    SCInputRef OpeningRangeStartTime = sc.Input[5];
    SCInputRef OpeningRangeEndTime = sc.Input[6];
    SCInputRef SetupStartTime = sc.Input[7];
    SCInputRef SetupEndTime = sc.Input[8];
    SCInputRef MinimumOpeningRangeWidthPoints = sc.Input[9];
    SCInputRef MinimumSweepPoints = sc.Input[10];
    SCInputRef MaximumReversalBars = sc.Input[11];
    SCInputRef CloseBackInsidePoints = sc.Input[12];
    SCInputRef StopBufferPoints = sc.Input[13];
    SCInputRef MaximumRiskPoints = sc.Input[14];
    SCInputRef MinimumTotalVolume = sc.Input[15];
    SCInputRef MinimumAggressiveDelta = sc.Input[16];
    SCInputRef MinimumAggressionRatio = sc.Input[17];
    SCInputRef ShortMaxCloseLocation = sc.Input[18];
    SCInputRef LongMinCloseLocation = sc.Input[19];
    SCInputRef Confidence = sc.Input[20];

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade Liquidity Sweep Signal Overlay";
        sc.StudyDescription = "Indicator-only liquidity sweep absorption overlay and signal-log CSV writer.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_SignalLog.csv");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString("replay");

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(1);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        OneSignalPerSidePerDay.Name = "One Signal Per Side Per Day";
        OneSignalPerSidePerDay.SetYesNo(1);

        OpeningRangeStartTime.Name = "Opening Range Start Time";
        OpeningRangeStartTime.SetTime(HMS_TIME(9, 30, 0));

        OpeningRangeEndTime.Name = "Opening Range End Time";
        OpeningRangeEndTime.SetTime(HMS_TIME(9, 59, 59));

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(10, 30, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(15, 15, 0));

        MinimumOpeningRangeWidthPoints.Name = "Minimum Opening Range Width Points";
        MinimumOpeningRangeWidthPoints.SetFloat(1.0f);

        MinimumSweepPoints.Name = "Minimum Sweep Points";
        MinimumSweepPoints.SetFloat(1.0f);

        MaximumReversalBars.Name = "Maximum Reversal Bars";
        MaximumReversalBars.SetInt(5);
        MaximumReversalBars.SetIntLimits(1, 100);

        CloseBackInsidePoints.Name = "Close Back Inside Points";
        CloseBackInsidePoints.SetFloat(0.25f);

        StopBufferPoints.Name = "Stop Buffer Points";
        StopBufferPoints.SetFloat(0.25f);

        MaximumRiskPoints.Name = "Maximum Risk Points";
        MaximumRiskPoints.SetFloat(20.0f);

        MinimumTotalVolume.Name = "Minimum Total Volume";
        MinimumTotalVolume.SetFloat(0.0f);

        MinimumAggressiveDelta.Name = "Minimum Aggressive Delta";
        MinimumAggressiveDelta.SetFloat(0.0f);

        MinimumAggressionRatio.Name = "Minimum Aggression Ratio";
        MinimumAggressionRatio.SetFloat(1.25f);

        ShortMaxCloseLocation.Name = "Short Max Close Location";
        ShortMaxCloseLocation.SetFloat(0.45f);

        LongMinCloseLocation.Name = "Long Min Close Location";
        LongMinCloseLocation.SetFloat(0.55f);

        Confidence.Name = "Research Confidence";
        Confidence.SetFloat(0.55f);

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
        last_processed_bar_index = -1;
    else if (latest_closed_bar_index < last_processed_bar_index)
        last_processed_bar_index = latest_closed_bar_index - 1;

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
            OpeningRangeStartTime.GetTime(),
            OpeningRangeEndTime.GetTime(),
            SetupStartTime.GetTime(),
            SetupEndTime.GetTime(),
            MinimumOpeningRangeWidthPoints.GetFloat(),
            MinimumSweepPoints.GetFloat(),
            MaximumReversalBars.GetInt(),
            CloseBackInsidePoints.GetFloat(),
            StopBufferPoints.GetFloat(),
            MaximumRiskPoints.GetFloat(),
            MinimumTotalVolume.GetFloat(),
            MinimumAggressiveDelta.GetFloat(),
            MinimumAggressionRatio.GetFloat(),
            ShortMaxCloseLocation.GetFloat(),
            LongMinCloseLocation.GetFloat());

        const std::string generated_at = ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]));
        const std::string signal_id = SignalId(symbol, bar_index);
        std::string event_key = EventKey(
            symbol,
            sc.ChartNumber,
            bar_index,
            evaluation.event_type,
            evaluation.direction);

        if (evaluation.event_type == "candidate_signal" && OneSignalPerSidePerDay.GetYesNo() != 0)
        {
            const std::string date_key = FormatDateKey(sc.BaseDateTimeIn[bar_index]);
            const std::string day_side_key = CandidateDaySideKey(
                symbol,
                sc.ChartNumber,
                date_key,
                evaluation.direction);
            const std::string candidate_event_key =
                day_side_key + ':' + FormatNumber(static_cast<double>(bar_index));
            if (FileContainsText(csv_log_path, candidate_event_key))
            {
                event_key = candidate_event_key;
            }
            else if (FileContainsText(csv_log_path, day_side_key))
            {
                evaluation = Rejection(
                    sc.BaseDataIn[SC_LAST][bar_index],
                    "duplicate_signal",
                    "liquidity sweep signal already emitted for this symbol/date/side");
                event_key = EventKey(symbol, sc.ChartNumber, bar_index, evaluation.event_type, evaluation.direction);
            }
            else
            {
                event_key = candidate_event_key;
            }
        }

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
                evaluation.target_price,
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
