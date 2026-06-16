#include "sierrachart.h"

#include <fstream>
#include <sstream>
#include <string>

SCDLLName("AxonTrade Simulation Safe Studies")

namespace
{
const int kLineDrawingNumber = 7001001;
const int kLabelDrawingNumber = 7001002;

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

void AppendCsvRowIfMissing(
    const std::string& file_path,
    const std::string& event_key,
    const std::string& timestamp,
    const std::string& symbol,
    int chart_number,
    int bar_index,
    double price,
    const std::string& event_type)
{
    if (FileContainsEventKey(file_path, event_key))
        return;

    const bool file_already_exists = static_cast<bool>(std::ifstream(file_path.c_str()));

    std::ofstream output(file_path.c_str(), std::ios::app);
    if (!output.is_open())
        return;

    if (!file_already_exists)
        output << "event_key,timestamp,symbol,chart_number,bar_index,price,event_type\n";

    output << event_key << ','
           << timestamp << ','
           << symbol << ','
           << chart_number << ','
           << bar_index << ','
           << price << ','
           << event_type << '\n';
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
        EventType.SetString("smoke_signal_created");

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString("AxonTrade_OrderFlowSignalSmokeTest.csv");

        LineColor.Name = "Line Color";
        LineColor.SetColor(RGB(0, 128, 255));

        LineWidth.Name = "Line Width";
        LineWidth.SetInt(2);

        return;
    }

    if (sc.ArraySize <= 0)
        return;

    const int latest_bar_index = sc.ArraySize - 1;
    const double line_price = LinePrice.GetFloat();

    // s_UseTool is Sierra Chart's drawing API. A stable LineNumber plus
    // UTAM_ADD_OR_ADJUST updates the same drawing during recalculation.
    s_UseTool line_tool;
    line_tool.Clear();
    line_tool.ChartNumber = sc.ChartNumber;
    line_tool.DrawingType = DRAWING_HORIZONTALLINE;
    line_tool.LineNumber = kLineDrawingNumber;
    line_tool.Region = 0;
    line_tool.BeginValue = line_price;
    line_tool.Color = LineColor.GetColor();
    line_tool.LineWidth = LineWidth.GetInt();
    line_tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(line_tool);

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

    int& logged_this_session = sc.GetPersistentInt(1);
    if (logged_this_session != 0)
        return;

    const SCString timestamp = sc.FormatDateTime(sc.BaseDateTimeIn[latest_bar_index]);
    const std::string symbol = ToStdString(sc.Symbol);
    const std::string event_type = ToStdString(EventType.GetString());
    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());

    std::ostringstream key_builder;
    key_builder << symbol << ':'
                << sc.ChartNumber << ':'
                << latest_bar_index << ':'
                << line_price << ':'
                << event_type;

    AppendCsvRowIfMissing(
        csv_log_path,
        key_builder.str(),
        ToStdString(timestamp),
        symbol,
        sc.ChartNumber,
        latest_bar_index,
        line_price,
        event_type);

    logged_this_session = 1;
}
