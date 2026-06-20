#include "sierrachart.h"

#include <fstream>
#include <iomanip>
#include <string>

SCDLLName("AxonTrade Volume At Price Logger")

namespace
{
std::string ToStdString(const SCString& value)
{
    return std::string(value.GetChars());
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

void LogMessage(SCStudyInterfaceRef sc, const char* text, int show_popup = 0)
{
    sc.AddMessageToLog(text, show_popup);
}
}

SCSFExport scsf_AxonTradeVolumeAtPriceLogger(SCStudyInterfaceRef sc)
{
    SCInputRef ExportNow = sc.Input[0];
    SCInputRef OutputFilePath = sc.Input[1];
    SCInputRef SessionPhase = sc.Input[2];
    SCInputRef MaxBarsToExport = sc.Input[3];
    SCInputRef IncludeHeader = sc.Input[4];
    SCInputRef LogSummary = sc.Input[5];

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade Volume At Price CSV Logger";
        sc.StudyDescription = "Indicator-only logger that writes one CSV row per chart bar price level.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 0;
        sc.MaintainVolumeAtPriceData = 1;

        ExportNow.Name = "Export Now";
        ExportNow.SetYesNo(0);

        OutputFilePath.Name = "Output File Path";
        OutputFilePath.SetString("C:\\SierraChart\\Data\\AxonTrade_ES_VolumeAtPriceExport.txt");

        SessionPhase.Name = "Session Phase";
        SessionPhase.SetString("rth");

        MaxBarsToExport.Name = "Max Bars To Export (0 = All Loaded Bars)";
        MaxBarsToExport.SetInt(0);
        MaxBarsToExport.SetIntLimits(0, INT_MAX);

        IncludeHeader.Name = "Include Header";
        IncludeHeader.SetYesNo(1);

        LogSummary.Name = "Log Summary";
        LogSummary.SetYesNo(1);

        return;
    }

    if (ExportNow.GetYesNo() == 0)
        return;

    ExportNow.SetYesNo(0);

    if (sc.ArraySize <= 0)
    {
        LogMessage(sc, "AxonTrade VAP export skipped: chart has no bars.", 1);
        return;
    }

    if (sc.TickSize <= 0)
    {
        LogMessage(sc, "AxonTrade VAP export skipped: chart Tick Size is not positive.", 1);
        return;
    }

    if (sc.VolumeAtPriceForBars == nullptr)
    {
        LogMessage(sc, "AxonTrade VAP export skipped: VolumeAtPriceForBars is not available.", 1);
        return;
    }

    if (static_cast<int>(sc.VolumeAtPriceForBars->GetNumberOfBars()) < sc.ArraySize)
    {
        LogMessage(sc, "AxonTrade VAP export skipped: volume-at-price data is not ready for all loaded bars.", 1);
        return;
    }

    const std::string output_file_path = ToStdString(OutputFilePath.GetString());
    if (output_file_path.empty())
    {
        LogMessage(sc, "AxonTrade VAP export skipped: Output File Path is blank.", 1);
        return;
    }

    std::ofstream output(output_file_path.c_str(), std::ios::out | std::ios::trunc);
    if (!output.is_open())
    {
        LogMessage(sc, "AxonTrade VAP export failed: could not open output file.", 1);
        return;
    }

    if (IncludeHeader.GetYesNo() != 0)
    {
        output << "timestamp,symbol,chart_number,bar_index,open,high,low,close,"
               << "price,bid_volume,ask_volume,level_volume,delta,number_of_trades,session_phase\n";
    }

    const std::string symbol = ToStdString(sc.Symbol);
    const std::string session_phase = ToStdString(SessionPhase.GetString());
    const int max_bars_to_export = MaxBarsToExport.GetInt();
    const int start_bar_index =
        (max_bars_to_export > 0 && max_bars_to_export < sc.ArraySize)
            ? sc.ArraySize - max_bars_to_export
            : 0;

    int rows_written = 0;
    int bars_with_vap = 0;
    output << std::setprecision(10);

    for (int bar_index = start_bar_index; bar_index < sc.ArraySize; ++bar_index)
    {
        const int vap_size_at_bar_index = sc.VolumeAtPriceForBars->GetSizeAtBarIndex(bar_index);
        if (vap_size_at_bar_index <= 0)
            continue;

        ++bars_with_vap;
        const std::string timestamp = ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]));

        for (int vap_index = 0; vap_index < vap_size_at_bar_index; ++vap_index)
        {
            const s_VolumeAtPriceV2* volume_at_price = nullptr;
            if (!sc.VolumeAtPriceForBars->GetVAPElementAtIndex(bar_index, vap_index, &volume_at_price))
                break;
            if (volume_at_price == nullptr)
                continue;

            const double price = static_cast<double>(volume_at_price->PriceInTicks) * sc.TickSize;
            const double bid_volume = volume_at_price->GetBidVolume();
            const double ask_volume = volume_at_price->GetAskVolume();
            const double level_volume = volume_at_price->GetVolume();
            const double delta = ask_volume - bid_volume;

            output << EscapeCsv(timestamp) << ','
                   << EscapeCsv(symbol) << ','
                   << sc.ChartNumber << ','
                   << bar_index << ','
                   << sc.BaseDataIn[SC_OPEN][bar_index] << ','
                   << sc.BaseDataIn[SC_HIGH][bar_index] << ','
                   << sc.BaseDataIn[SC_LOW][bar_index] << ','
                   << sc.BaseDataIn[SC_LAST][bar_index] << ','
                   << price << ','
                   << bid_volume << ','
                   << ask_volume << ','
                   << level_volume << ','
                   << delta << ','
                   << volume_at_price->NumberOfTrades << ','
                   << EscapeCsv(session_phase) << '\n';
            ++rows_written;
        }
    }

    output.close();

    if (LogSummary.GetYesNo() != 0)
    {
        SCString message;
        message.Format(
            "AxonTrade VAP export complete: rows=%d bars_with_vap=%d file=%s",
            rows_written,
            bars_with_vap,
            output_file_path.c_str());
        sc.AddMessageToLog(message, 0);
    }
}
