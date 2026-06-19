#include "sierrachart.h"

#include <fstream>
#include <sstream>
#include <string>

SCDLLName("AxonTrade Simulation Safe Studies")

namespace
{
const int kLineDrawingNumber = 7001001;
const int kLabelDrawingNumber = 7001002;
const int kStopDrawingNumber = 7001003;
const int kTargetDrawingNumber = 7001004;
const int kInvalidationDrawingNumber = 7001005;

std::string ToStdString(const SCString& value)
{
    return std::string(value.GetChars());
}

bool FileContainsEventKey(const std::string& file_path, const std::string& event_key)
{
    std::ifstream input(file_path.c_str());
    if (!input.is_open())
        return false;

    std::string line;
    while (std::getline(input, line))
    {
        if (line.find(event_key) != std::string::npos)
            return true;
    }

    return false;
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
    double signal_price,
    double stop_price,
    double target_price,
    double invalidation_price,
    const std::string& rejection_reason,
    double confidence,
    const std::string& notes)
{
    if (FileContainsEventKey(file_path, event_key))
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

bool IsShortDirection(const std::string& direction)
{
    return direction == "short" || direction == "Short" || direction == "SHORT";
}

void DrawHorizontalReference(
    SCStudyInterfaceRef sc,
    int drawing_number,
    double price,
    COLORREF color,
    int line_width)
{
    s_UseTool tool;
    tool.Clear();
    tool.ChartNumber = sc.ChartNumber;
    tool.DrawingType = DRAWING_HORIZONTALLINE;
    tool.LineNumber = drawing_number;
    tool.Region = 0;
    tool.BeginValue = price;
    tool.Color = color;
    tool.LineWidth = line_width;
    tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(tool);
}
}

SCSFExport scsf_OrderFlowSignalSmokeTest(SCStudyInterfaceRef sc)
{
    SCInputRef LinePrice = sc.Input[0];
    SCInputRef LabelText = sc.Input[1];
    SCInputRef EventType = sc.Input[2];
    SCInputRef CsvLogPath = sc.Input[3];
    SCInputRef LineColor = sc.Input[4];
    SCInputRef LineWidth = sc.Input[5];
    SCInputRef Direction = sc.Input[6];
    SCInputRef Action = sc.Input[7];
    SCInputRef StrategyId = sc.Input[8];
    SCInputRef SignalId = sc.Input[9];
    SCInputRef TradeMode = sc.Input[10];
    SCInputRef StopOffsetPoints = sc.Input[11];
    SCInputRef TargetOffsetPoints = sc.Input[12];
    SCInputRef RejectionReason = sc.Input[13];
    SCInputRef Confidence = sc.Input[14];
    SCInputRef Notes = sc.Input[15];

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade Order Flow Signal Smoke Test";
        sc.StudyDescription = "Indicator-only smoke test for deterministic drawings and CSV logging.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 0;

        LinePrice.Name = "Horizontal Line Price";
        LinePrice.SetFloat(5000.0f);

        LabelText.Name = "Label Text";
        LabelText.SetString("AxonTrade smoke test");

        EventType.Name = "Event Type";
        EventType.SetString("candidate_signal");

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString("AxonTrade_OrderFlowSignalSmokeTest.csv");

        LineColor.Name = "Line Color";
        LineColor.SetColor(RGB(0, 128, 255));

        LineWidth.Name = "Line Width";
        LineWidth.SetInt(2);

        Direction.Name = "Direction";
        Direction.SetString("long");

        Action.Name = "Action";
        Action.SetString("candidate");

        StrategyId.Name = "Strategy ID";
        StrategyId.SetString("manual_smoke_signal");

        SignalId.Name = "Signal ID";
        SignalId.SetString("manual_smoke_signal_001");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString("sim");

        StopOffsetPoints.Name = "Stop Offset Points";
        StopOffsetPoints.SetFloat(4.0f);

        TargetOffsetPoints.Name = "Target Offset Points";
        TargetOffsetPoints.SetFloat(8.0f);

        RejectionReason.Name = "Rejection Reason";
        RejectionReason.SetString("not_applicable");

        Confidence.Name = "Research Confidence";
        Confidence.SetFloat(0.5f);

        Notes.Name = "Notes";
        Notes.SetString("indicator-only schema smoke row");

        return;
    }

    if (sc.ArraySize <= 0)
        return;

    const int latest_bar_index = sc.ArraySize - 1;
    const double line_price = LinePrice.GetFloat();
    const std::string direction = ToStdString(Direction.GetString());
    const bool short_direction = IsShortDirection(direction);
    const double stop_offset = StopOffsetPoints.GetFloat();
    const double target_offset = TargetOffsetPoints.GetFloat();
    const double stop_price = short_direction ? line_price + stop_offset : line_price - stop_offset;
    const double target_price = short_direction ? line_price - target_offset : line_price + target_offset;
    const double invalidation_price = stop_price;

    // s_UseTool is Sierra Chart's drawing API. A stable LineNumber plus
    // UTAM_ADD_OR_ADJUST updates the same drawing during recalculation.
    DrawHorizontalReference(sc, kLineDrawingNumber, line_price, LineColor.GetColor(), LineWidth.GetInt());
    DrawHorizontalReference(sc, kStopDrawingNumber, stop_price, RGB(220, 64, 64), 1);
    DrawHorizontalReference(sc, kTargetDrawingNumber, target_price, RGB(64, 180, 255), 1);
    DrawHorizontalReference(sc, kInvalidationDrawingNumber, invalidation_price, RGB(255, 180, 0), 1);

    s_UseTool label_tool;
    label_tool.Clear();
    label_tool.ChartNumber = sc.ChartNumber;
    label_tool.DrawingType = DRAWING_TEXT;
    label_tool.LineNumber = kLabelDrawingNumber;
    label_tool.Region = 0;
    label_tool.BeginIndex = latest_bar_index;
    label_tool.BeginValue = line_price;
    label_tool.Color = LineColor.GetColor();
    label_tool.FontSize = 10;
    label_tool.Text = LabelText.GetString();
    label_tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label_tool);

    const SCString timestamp = sc.FormatDateTime(sc.BaseDateTimeIn[latest_bar_index]);
    const std::string symbol = ToStdString(sc.Symbol);
    const std::string event_type = ToStdString(EventType.GetString());
    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    const std::string strategy_id = ToStdString(StrategyId.GetString());
    const std::string signal_id = ToStdString(SignalId.GetString());
    const std::string action = ToStdString(Action.GetString());
    const std::string trade_mode = ToStdString(TradeMode.GetString());
    const std::string rejection_reason = ToStdString(RejectionReason.GetString());
    const std::string notes = ToStdString(Notes.GetString());

    std::ostringstream key_builder;
    key_builder << symbol << ':'
                << sc.ChartNumber << ':'
                << latest_bar_index << ':'
                << line_price << ':'
                << strategy_id << ':'
                << signal_id << ':'
                << event_type;

    AppendSignalLogRowIfMissing(
        csv_log_path,
        key_builder.str(),
        event_type,
        ToStdString(timestamp),
        symbol,
        sc.ChartNumber,
        latest_bar_index,
        ToStdString(timestamp),
        trade_mode,
        strategy_id,
        signal_id,
        direction,
        action,
        line_price,
        stop_price,
        target_price,
        invalidation_price,
        rejection_reason,
        Confidence.GetFloat(),
        notes);

}
