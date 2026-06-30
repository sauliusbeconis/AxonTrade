#include "sierrachart.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

SCDLLName("AxonTrade VWAP Delta Live Sim Bot")

namespace
{
const char* kStrategyId =
    "vwap_delta_exhaustion_fade_2pt_10d_cl0.5_guard_risk175_exit6_10_12_initial_health3600_4000";
const int kDrawingBase = 8600000;

struct PaperTrade
{
    int trade_id = 0;
    int entry_bar_index = 0;
    int entry_date = 0;
    std::string signal_id;
    std::string direction;
    double entry_price = 0.0;
    double stop_price = 0.0;
    double first_target_price = 0.0;
    double runner_target_price = 0.0;
    int first_leg_quantity = 1;
    int runner_quantity = 1;
    bool leg1_open = true;
    bool runner_open = true;
    double leg1_exit_price = 0.0;
    double runner_exit_price = 0.0;
    std::string final_exit_reason;
};

struct SignalCandidate
{
    bool has_raw_setup = false;
    bool accepted = false;
    std::string direction = "none";
    std::string action = "reject";
    std::string rejection_reason = "no_setup";
    std::string notes = "no setup";
    double entry_price = 0.0;
    double stop_price = 0.0;
    double first_target_price = 0.0;
    double runner_target_price = 0.0;
    double vwap = 0.0;
    double distance_from_vwap = 0.0;
    double delta = 0.0;
    double close_location = 0.5;
    double session_range_points = 0.0;
    double average_bar_range_points = 0.0;
    double risk_to_average_bar_range = 0.0;
    double lookback_directional_move_points = 0.0;
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

std::string FormatBool(bool value)
{
    return value ? "true" : "false";
}

bool SameChartDate(const SCDateTime& left, const SCDateTime& right)
{
    return left.GetDate() == right.GetDate();
}

double HlcAverage(SCStudyInterfaceRef sc, int bar_index)
{
    return (
        sc.BaseDataIn[SC_HIGH][bar_index]
        + sc.BaseDataIn[SC_LOW][bar_index]
        + sc.BaseDataIn[SC_LAST][bar_index]) / 3.0;
}

double BarVolume(SCStudyInterfaceRef sc, int bar_index)
{
    const double volume = sc.BaseDataIn[SC_VOLUME][bar_index];
    return volume > 0.0 ? volume : 0.0;
}

double BarDelta(SCStudyInterfaceRef sc, int bar_index)
{
    return sc.BaseDataIn[SC_ASKVOL][bar_index] - sc.BaseDataIn[SC_BIDVOL][bar_index];
}

double CloseLocation(SCStudyInterfaceRef sc, int bar_index)
{
    const double high = sc.BaseDataIn[SC_HIGH][bar_index];
    const double low = sc.BaseDataIn[SC_LOW][bar_index];
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    if (high <= low)
        return 0.5;
    return (close - low) / (high - low);
}

double SessionVwapAtBar(SCStudyInterfaceRef sc, int bar_index)
{
    double price_volume = 0.0;
    double volume_sum = 0.0;
    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];

    for (int index = bar_index; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;

        const double volume = BarVolume(sc, index);
        if (volume > 0.0)
        {
            price_volume += HlcAverage(sc, index) * volume;
            volume_sum += volume;
        }
    }

    if (volume_sum <= 0.0)
        return sc.BaseDataIn[SC_LAST][bar_index];
    return price_volume / volume_sum;
}

double SessionRangeAtBar(SCStudyInterfaceRef sc, int bar_index)
{
    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];
    double high = sc.BaseDataIn[SC_HIGH][bar_index];
    double low = sc.BaseDataIn[SC_LOW][bar_index];

    for (int index = bar_index - 1; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;
        high = sc.BaseDataIn[SC_HIGH][index] > high ? sc.BaseDataIn[SC_HIGH][index] : high;
        low = sc.BaseDataIn[SC_LOW][index] < low ? sc.BaseDataIn[SC_LOW][index] : low;
    }

    return high - low;
}

bool PreviousContextStats(
    SCStudyInterfaceRef sc,
    int bar_index,
    int lookback_bars,
    const std::string& direction,
    double& average_bar_range_points,
    double& lookback_directional_move_points)
{
    if (lookback_bars <= 0)
        return false;

    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];
    std::vector<int> previous_indices;
    for (int index = bar_index - 1; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;
        previous_indices.push_back(index);
        if (static_cast<int>(previous_indices.size()) >= lookback_bars)
            break;
    }

    if (static_cast<int>(previous_indices.size()) < lookback_bars)
        return false;

    double range_sum = 0.0;
    for (std::vector<int>::const_iterator index = previous_indices.begin();
         index != previous_indices.end();
         ++index)
    {
        range_sum += sc.BaseDataIn[SC_HIGH][*index] - sc.BaseDataIn[SC_LOW][*index];
    }
    average_bar_range_points = range_sum / static_cast<double>(lookback_bars);

    const int oldest_previous_index = previous_indices[lookback_bars - 1];
    const double start_price = sc.BaseDataIn[SC_LAST][oldest_previous_index];
    const double end_price = sc.BaseDataIn[SC_LAST][bar_index];
    if (direction == "long")
        lookback_directional_move_points = end_price - start_price;
    else
        lookback_directional_move_points = start_price - end_price;
    return true;
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

std::vector<PaperTrade>* GetOpenTrades(SCStudyInterfaceRef sc)
{
    std::vector<PaperTrade>* trades = static_cast<std::vector<PaperTrade>*>(sc.GetPersistentPointer(1));
    if (trades == 0)
    {
        trades = new std::vector<PaperTrade>();
        sc.SetPersistentPointer(1, trades);
    }
    return trades;
}

void DeleteOpenTrades(SCStudyInterfaceRef sc)
{
    std::vector<PaperTrade>* trades = static_cast<std::vector<PaperTrade>*>(sc.GetPersistentPointer(1));
    if (trades != 0)
    {
        delete trades;
        sc.SetPersistentPointer(1, static_cast<void*>(0));
    }
}

void AppendBotLogRow(
    const std::string& file_path,
    const std::string& event_type,
    const std::string& timestamp,
    const std::string& symbol,
    int chart_number,
    int bar_index,
    const std::string& trade_mode,
    const std::string& signal_id,
    int paper_trade_id,
    const std::string& direction,
    const std::string& action,
    double price,
    double entry_price,
    double stop_price,
    double first_target_price,
    double runner_target_price,
    const std::string& exit_reason,
    int quantity,
    bool leg1_open,
    bool runner_open,
    double gross_points,
    double gross_usd,
    double commission_usd,
    double slippage_usd,
    double net_usd,
    double daily_net_usd,
    double accepted_equity_usd,
    double accepted_drawdown_usd,
    const std::string& rejection_reason,
    const std::string& notes)
{
    std::ifstream existing_file(file_path.c_str());
    const bool file_already_exists = existing_file.good();
    existing_file.close();
    std::ofstream output(file_path.c_str(), std::ios::app);
    if (!output.is_open())
        return;

    if (!file_already_exists)
    {
        output << "schema_version,event_type,timestamp,symbol,chart_number,bar_index,"
               << "trade_mode,strategy_id,signal_id,paper_trade_id,direction,action,"
               << "price,entry_price,stop_price,first_target_price,runner_target_price,"
               << "exit_reason,quantity,leg1_open,runner_open,gross_points,gross_usd,"
               << "commission_usd,slippage_usd,net_usd,daily_net_usd,"
               << "accepted_equity_usd,accepted_drawdown_usd,rejection_reason,notes\n";
    }

    output << 1 << ','
           << EscapeCsv(event_type) << ','
           << EscapeCsv(timestamp) << ','
           << EscapeCsv(symbol) << ','
           << chart_number << ','
           << bar_index << ','
           << EscapeCsv(trade_mode) << ','
           << EscapeCsv(kStrategyId) << ','
           << EscapeCsv(signal_id) << ','
           << paper_trade_id << ','
           << EscapeCsv(direction) << ','
           << EscapeCsv(action) << ','
           << FormatNumber(price) << ','
           << FormatNumber(entry_price) << ','
           << FormatNumber(stop_price) << ','
           << FormatNumber(first_target_price) << ','
           << FormatNumber(runner_target_price) << ','
           << EscapeCsv(exit_reason) << ','
           << quantity << ','
           << FormatBool(leg1_open) << ','
           << FormatBool(runner_open) << ','
           << FormatNumber(gross_points) << ','
           << FormatNumber(gross_usd) << ','
           << FormatNumber(commission_usd) << ','
           << FormatNumber(slippage_usd) << ','
           << FormatNumber(net_usd) << ','
           << FormatNumber(daily_net_usd) << ','
           << FormatNumber(accepted_equity_usd) << ','
           << FormatNumber(accepted_drawdown_usd) << ','
           << EscapeCsv(rejection_reason) << ','
           << EscapeCsv(notes) << '\n';
}

std::string SignalId(const std::string& symbol, int bar_index, const std::string& direction)
{
    std::ostringstream output;
    output << kStrategyId << '_' << symbol << '_' << bar_index << '_' << direction;
    return output.str();
}

bool StopHit(const PaperTrade& trade, SCStudyInterfaceRef sc, int bar_index)
{
    if (trade.direction == "long")
        return sc.BaseDataIn[SC_LOW][bar_index] <= trade.stop_price;
    return sc.BaseDataIn[SC_HIGH][bar_index] >= trade.stop_price;
}

bool FirstTargetHit(const PaperTrade& trade, SCStudyInterfaceRef sc, int bar_index)
{
    if (trade.direction == "long")
        return sc.BaseDataIn[SC_HIGH][bar_index] >= trade.first_target_price;
    return sc.BaseDataIn[SC_LOW][bar_index] <= trade.first_target_price;
}

bool RunnerTargetHit(const PaperTrade& trade, SCStudyInterfaceRef sc, int bar_index)
{
    if (trade.direction == "long")
        return sc.BaseDataIn[SC_HIGH][bar_index] >= trade.runner_target_price;
    return sc.BaseDataIn[SC_LOW][bar_index] <= trade.runner_target_price;
}

double GrossPoints(const std::string& direction, double entry_price, double exit_price)
{
    if (direction == "long")
        return exit_price - entry_price;
    return entry_price - exit_price;
}

double TradeNetUsd(
    const PaperTrade& trade,
    double point_value_usd,
    double tick_value_usd,
    double commission_per_side_usd,
    double slippage_ticks_per_contract,
    double& gross_points,
    double& gross_usd,
    double& commission_usd,
    double& slippage_usd)
{
    const int total_quantity = trade.first_leg_quantity + trade.runner_quantity;
    gross_points =
        GrossPoints(trade.direction, trade.entry_price, trade.leg1_exit_price)
            * static_cast<double>(trade.first_leg_quantity)
        + GrossPoints(trade.direction, trade.entry_price, trade.runner_exit_price)
            * static_cast<double>(trade.runner_quantity);
    gross_usd = gross_points * point_value_usd;
    commission_usd = commission_per_side_usd * 2.0 * static_cast<double>(total_quantity);
    slippage_usd = slippage_ticks_per_contract * tick_value_usd * static_cast<double>(total_quantity);
    return gross_usd - commission_usd - slippage_usd;
}

void DrawEntryOverlay(SCStudyInterfaceRef sc, const PaperTrade& trade)
{
    const bool is_long = trade.direction == "long";
    const int direction_offset = is_long ? 0 : 200000;
    const int drawing_base = kDrawingBase + direction_offset + trade.entry_bar_index * 10;
    const COLORREF signal_color = is_long ? RGB(0, 180, 255) : RGB(255, 96, 80);
    const double tick_offset = sc.TickSize > 0.0 ? sc.TickSize * 2.0 : 1.0;
    const double marker_price = is_long
        ? sc.BaseDataIn[SC_LOW][trade.entry_bar_index] - tick_offset
        : sc.BaseDataIn[SC_HIGH][trade.entry_bar_index] + tick_offset;

    s_UseTool marker;
    marker.Clear();
    marker.ChartNumber = sc.ChartNumber;
    marker.DrawingType = DRAWING_MARKER;
    marker.LineNumber = drawing_base + 1;
    marker.Region = 0;
    marker.BeginIndex = trade.entry_bar_index;
    marker.BeginValue = marker_price;
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
    label.BeginIndex = trade.entry_bar_index;
    label.BeginValue = marker_price;
    label.Color = signal_color;
    label.FontSize = 9;
    label.Text = is_long ? "Axon paper long" : "Axon paper short";
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);
}

void DrawLineSegment(
    SCStudyInterfaceRef sc,
    int drawing_number,
    int start_bar_index,
    int end_bar_index,
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
    tool.BeginIndex = start_bar_index;
    tool.EndIndex = MinInt(sc.ArraySize - 1, end_bar_index);
    tool.BeginValue = price;
    tool.EndValue = price;
    tool.Color = color;
    tool.LineWidth = line_width;
    tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(tool);
}

void DrawTradeLevels(SCStudyInterfaceRef sc, const PaperTrade& trade)
{
    const int drawing_base = kDrawingBase + 400000 + trade.entry_bar_index * 10;
    const int end_bar_index = trade.entry_bar_index + 8;
    DrawLineSegment(sc, drawing_base + 1, trade.entry_bar_index, end_bar_index, trade.stop_price, RGB(220, 64, 64), 1);
    DrawLineSegment(sc, drawing_base + 2, trade.entry_bar_index, end_bar_index, trade.first_target_price, RGB(64, 180, 255), 1);
    DrawLineSegment(sc, drawing_base + 3, trade.entry_bar_index, end_bar_index, trade.runner_target_price, RGB(64, 220, 120), 2);
}

void DrawExitMarker(SCStudyInterfaceRef sc, const PaperTrade& trade, int bar_index, double price, const std::string& text)
{
    const int drawing_base = kDrawingBase + 600000 + trade.trade_id * 10;
    s_UseTool marker;
    marker.Clear();
    marker.ChartNumber = sc.ChartNumber;
    marker.DrawingType = DRAWING_MARKER;
    marker.LineNumber = drawing_base + 1;
    marker.Region = 0;
    marker.BeginIndex = bar_index;
    marker.BeginValue = price;
    marker.MarkerType = MARKER_DIAMOND;
    marker.MarkerSize = 7;
    marker.LineWidth = 4;
    marker.Color = RGB(255, 205, 64);
    marker.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(marker);

    s_UseTool label;
    label.Clear();
    label.ChartNumber = sc.ChartNumber;
    label.DrawingType = DRAWING_TEXT;
    label.LineNumber = drawing_base + 2;
    label.Region = 0;
    label.BeginIndex = bar_index;
    label.BeginValue = price;
    label.Color = RGB(255, 205, 64);
    label.FontSize = 8;
    label.Text = text.c_str();
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);
}

bool RawPacingAllowed(
    SCStudyInterfaceRef sc,
    int bar_index,
    int minimum_spacing_seconds,
    int max_raw_candidates_per_day,
    std::string& rejection_reason,
    std::string& notes)
{
    int& raw_signal_date = sc.GetPersistentInt(2);
    int& raw_signal_count = sc.GetPersistentInt(3);
    int& last_raw_signal_time = sc.GetPersistentInt(4);

    const int current_date = sc.BaseDateTimeIn[bar_index].GetDate();
    const int current_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
    if (raw_signal_date != current_date)
    {
        raw_signal_date = current_date;
        raw_signal_count = 0;
        last_raw_signal_time = -1;
    }

    if (max_raw_candidates_per_day > 0 && raw_signal_count >= max_raw_candidates_per_day)
    {
        rejection_reason = "raw_candidate_daily_limit";
        notes = "maximum raw VWAP/delta candidates reached for this chart date";
        return false;
    }
    if (last_raw_signal_time >= 0 && minimum_spacing_seconds > 0)
    {
        const int seconds_since_last = current_time - last_raw_signal_time;
        if (seconds_since_last >= 0 && seconds_since_last < minimum_spacing_seconds)
        {
            rejection_reason = "raw_candidate_spacing_filter";
            std::ostringstream output;
            output << "last raw VWAP/delta candidate was "
                   << seconds_since_last
                   << " seconds ago, below minimum spacing";
            notes = output.str();
            return false;
        }
    }
    return true;
}

void RecordRawCandidate(SCStudyInterfaceRef sc, int bar_index)
{
    int& raw_signal_date = sc.GetPersistentInt(2);
    int& raw_signal_count = sc.GetPersistentInt(3);
    int& last_raw_signal_time = sc.GetPersistentInt(4);

    raw_signal_date = sc.BaseDateTimeIn[bar_index].GetDate();
    raw_signal_count += 1;
    last_raw_signal_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
}

void EnsureHealthDate(SCStudyInterfaceRef sc, int bar_index)
{
    int& health_date = sc.GetPersistentInt(6);
    int& health_block_day = sc.GetPersistentInt(7);
    int& health_block_reason = sc.GetPersistentInt(10);
    const int current_date = sc.BaseDateTimeIn[bar_index].GetDate();
    if (health_date != current_date)
    {
        health_date = current_date;
        health_block_day = 0;
        health_block_reason = 0;
        sc.GetPersistentDouble(1) = 0.0;
    }
}

double AcceptedDrawdown(SCStudyInterfaceRef sc)
{
    const double equity = sc.GetPersistentDouble(2);
    const double peak = sc.GetPersistentDouble(3);
    return equity - peak;
}

void ApplyRealizedHealthUpdate(
    SCStudyInterfaceRef sc,
    int bar_index,
    double net_usd,
    double daily_loss_limit_usd,
    double daily_profit_lock_usd,
    double max_accepted_drawdown_usd)
{
    EnsureHealthDate(sc, bar_index);
    double& daily_net = sc.GetPersistentDouble(1);
    double& accepted_equity = sc.GetPersistentDouble(2);
    double& peak_equity = sc.GetPersistentDouble(3);
    int& health_block_day = sc.GetPersistentInt(7);
    int& health_block_reason = sc.GetPersistentInt(10);

    daily_net += net_usd;
    accepted_equity += net_usd;
    if (accepted_equity > peak_equity)
        peak_equity = accepted_equity;

    const double drawdown = accepted_equity - peak_equity;
    if (daily_loss_limit_usd > 0.0 && daily_net <= -daily_loss_limit_usd)
    {
        health_block_day = 1;
        health_block_reason = 1;
    }
    if (daily_profit_lock_usd > 0.0 && daily_net >= daily_profit_lock_usd)
    {
        health_block_day = 1;
        health_block_reason = 3;
    }
    if (max_accepted_drawdown_usd > 0.0 && drawdown <= -max_accepted_drawdown_usd)
    {
        health_block_day = 1;
        health_block_reason = 2;
        peak_equity = accepted_equity;
    }
}

bool HealthAllowsNewEntry(SCStudyInterfaceRef sc, int bar_index, std::string& rejection_reason, std::string& notes)
{
    EnsureHealthDate(sc, bar_index);
    if (sc.GetPersistentInt(7) == 0)
        return true;

    const int health_block_reason = sc.GetPersistentInt(10);
    if (health_block_reason == 1)
    {
        rejection_reason = "daily_loss_gate_blocked";
        notes = "paper bot is blocked for the rest of this chart date by realized daily loss";
    }
    else if (health_block_reason == 2)
    {
        rejection_reason = "accepted_equity_drawdown_gate_blocked";
        notes = "paper bot is blocked by accepted-equity drawdown";
    }
    else if (health_block_reason == 3)
    {
        rejection_reason = "daily_profit_lock_blocked";
        notes = "paper bot is locked for the rest of this chart date after reaching the daily profit lock";
    }
    else
    {
        rejection_reason = "health_gate_blocked";
        notes = "paper bot is blocked for the rest of this chart date by realized health gate";
    }
    return false;
}

SignalCandidate EvaluateCandidate(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    double vwap_extension_points,
    double delta_threshold,
    double close_location_threshold,
    int context_lookback_bars,
    double minimum_lookback_directional_move_points,
    double minimum_session_range_points,
    double max_risk_to_average_bar_range,
    double stop_points,
    double first_target_points,
    double runner_target_points)
{
    SignalCandidate candidate;
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
    candidate.entry_price = close;

    if (bar_time < setup_start_time || bar_time > setup_end_time)
    {
        candidate.rejection_reason = "outside_setup_window";
        candidate.notes = "closed bar is outside setup window";
        return candidate;
    }
    if (stop_points <= 0.0 || first_target_points <= 0.0 || runner_target_points <= first_target_points)
    {
        candidate.rejection_reason = "configuration_error";
        candidate.notes = "invalid fixed exit points";
        return candidate;
    }

    candidate.vwap = SessionVwapAtBar(sc, bar_index);
    candidate.distance_from_vwap = close - candidate.vwap;
    candidate.delta = BarDelta(sc, bar_index);
    candidate.close_location = CloseLocation(sc, bar_index);

    if (
        candidate.distance_from_vwap >= vwap_extension_points
        && candidate.delta >= delta_threshold
        && candidate.close_location <= close_location_threshold)
    {
        candidate.has_raw_setup = true;
        candidate.direction = "short";
    }
    else if (
        candidate.distance_from_vwap <= -vwap_extension_points
        && candidate.delta <= -delta_threshold
        && candidate.close_location >= 1.0 - close_location_threshold)
    {
        candidate.has_raw_setup = true;
        candidate.direction = "long";
    }
    else
    {
        std::ostringstream notes;
        notes << "distance_from_vwap=" << FormatNumber(candidate.distance_from_vwap)
              << "; delta=" << FormatNumber(candidate.delta)
              << "; close_location=" << FormatNumber(candidate.close_location)
              << "; raw thresholds not met";
        candidate.notes = notes.str();
        return candidate;
    }

    const bool is_long = candidate.direction == "long";
    candidate.stop_price = is_long ? close - stop_points : close + stop_points;
    candidate.first_target_price = is_long ? close + first_target_points : close - first_target_points;
    candidate.runner_target_price = is_long ? close + runner_target_points : close - runner_target_points;
    candidate.session_range_points = SessionRangeAtBar(sc, bar_index);

    if (!PreviousContextStats(
            sc,
            bar_index,
            context_lookback_bars,
            candidate.direction,
            candidate.average_bar_range_points,
            candidate.lookback_directional_move_points))
    {
        candidate.rejection_reason = "insufficient_context";
        candidate.notes = "not enough same-date bars for context guard";
        return candidate;
    }

    if (candidate.average_bar_range_points <= 0.0)
    {
        candidate.rejection_reason = "invalid_context";
        candidate.notes = "average bar range is not positive";
        return candidate;
    }

    candidate.risk_to_average_bar_range = stop_points / candidate.average_bar_range_points;
    if (candidate.lookback_directional_move_points > minimum_lookback_directional_move_points)
    {
        std::ostringstream notes;
        notes << "lookback_directional_move_points="
              << FormatNumber(candidate.lookback_directional_move_points)
              << " is above guard threshold "
              << FormatNumber(minimum_lookback_directional_move_points);
        candidate.rejection_reason = "lookback_fade_push_guard";
        candidate.notes = notes.str();
        return candidate;
    }
    if (candidate.session_range_points < minimum_session_range_points)
    {
        std::ostringstream notes;
        notes << "session_range_points=" << FormatNumber(candidate.session_range_points)
              << " is below guard threshold "
              << FormatNumber(minimum_session_range_points);
        candidate.rejection_reason = "session_range_guard";
        candidate.notes = notes.str();
        return candidate;
    }
    if (candidate.risk_to_average_bar_range > max_risk_to_average_bar_range)
    {
        std::ostringstream notes;
        notes << "risk_to_average_bar_range="
              << FormatNumber(candidate.risk_to_average_bar_range)
              << " is above guard threshold "
              << FormatNumber(max_risk_to_average_bar_range);
        candidate.rejection_reason = "risk_to_average_bar_range_guard";
        candidate.notes = notes.str();
        return candidate;
    }

    candidate.accepted = true;
    candidate.action = "paper_entry";
    candidate.rejection_reason = "not_applicable";
    std::ostringstream notes;
    notes << candidate.direction << " VWAP/delta exhaustion fade; "
          << "distance_from_vwap=" << FormatNumber(candidate.distance_from_vwap) << "; "
          << "delta=" << FormatNumber(candidate.delta) << "; "
          << "close_location=" << FormatNumber(candidate.close_location) << "; "
          << "lookback_directional_move_points=" << FormatNumber(candidate.lookback_directional_move_points) << "; "
          << "session_range_points=" << FormatNumber(candidate.session_range_points) << "; "
          << "risk_to_average_bar_range=" << FormatNumber(candidate.risk_to_average_bar_range);
    candidate.notes = notes.str();
    return candidate;
}

void LogCandidateRejection(
    SCStudyInterfaceRef sc,
    const std::string& csv_log_path,
    const std::string& symbol,
    const std::string& trade_mode,
    int bar_index,
    const SignalCandidate& candidate,
    const std::string& signal_id)
{
    const std::string timestamp = ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]));
    AppendBotLogRow(
        csv_log_path,
        "rejected_signal",
        timestamp,
        symbol,
        sc.ChartNumber,
        bar_index,
        trade_mode,
        signal_id,
        0,
        candidate.direction,
        "reject",
        candidate.entry_price,
        candidate.entry_price,
        candidate.stop_price,
        candidate.first_target_price,
        candidate.runner_target_price,
        "",
        0,
        false,
        false,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        sc.GetPersistentDouble(1),
        sc.GetPersistentDouble(2),
        AcceptedDrawdown(sc),
        candidate.rejection_reason,
        candidate.notes);
}
}

SCSFExport scsf_AxonTradeVwapDeltaLiveSimBot(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef TradeMode = sc.Input[1];
    SCInputRef EnablePaperEntries = sc.Input[2];
    SCInputRef LogRejections = sc.Input[3];
    SCInputRef ProcessFullRecalculation = sc.Input[4];
    SCInputRef ResetCsvOnFullRecalculation = sc.Input[5];
    SCInputRef SetupStartTime = sc.Input[6];
    SCInputRef SetupEndTime = sc.Input[7];
    SCInputRef FlattenTime = sc.Input[8];
    SCInputRef VwapExtensionPoints = sc.Input[9];
    SCInputRef DeltaThreshold = sc.Input[10];
    SCInputRef CloseLocationThreshold = sc.Input[11];
    SCInputRef MinimumSpacingSeconds = sc.Input[12];
    SCInputRef MaxRawCandidatesPerDay = sc.Input[13];
    SCInputRef ContextLookbackBars = sc.Input[14];
    SCInputRef MinimumLookbackDirectionalMovePoints = sc.Input[15];
    SCInputRef MinimumSessionRangePoints = sc.Input[16];
    SCInputRef MaxRiskToAverageBarRange = sc.Input[17];
    SCInputRef InitialStopPoints = sc.Input[18];
    SCInputRef FirstTargetPoints = sc.Input[19];
    SCInputRef RunnerTargetPoints = sc.Input[20];
    SCInputRef FirstLegQuantity = sc.Input[21];
    SCInputRef RunnerQuantity = sc.Input[22];
    SCInputRef DailyLossLimitUsd = sc.Input[23];
    SCInputRef DailyProfitLockUsd = sc.Input[24];
    SCInputRef MaxAcceptedDrawdownUsd = sc.Input[25];
    SCInputRef PointValueUsd = sc.Input[26];
    SCInputRef TickValueUsd = sc.Input[27];
    SCInputRef CommissionPerSideUsd = sc.Input[28];
    SCInputRef SlippageTicksPerContract = sc.Input[29];
    SCInputRef MaxOpenPaperTrades = sc.Input[30];

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade VWAP Delta Live Sim Bot";
        sc.StudyDescription = "Simulation-only VWAP/delta exhaustion paper bot with fixed guard, scaled exits, and realized health gate. It does not route orders.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_VwapDeltaLiveSimBot.csv");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString("live_sim");

        EnablePaperEntries.Name = "Enable Paper Entries";
        EnablePaperEntries.SetYesNo(1);

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(0);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        ResetCsvOnFullRecalculation.Name = "Reset CSV On Full Recalculation";
        ResetCsvOnFullRecalculation.SetYesNo(1);

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(9, 45, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(15, 45, 0));

        FlattenTime.Name = "Paper Flatten Time";
        FlattenTime.SetTime(HMS_TIME(16, 40, 0));

        VwapExtensionPoints.Name = "VWAP Extension Points";
        VwapExtensionPoints.SetFloat(2.0f);

        DeltaThreshold.Name = "Minimum Bar Delta";
        DeltaThreshold.SetFloat(10.0f);

        CloseLocationThreshold.Name = "Close Location Threshold";
        CloseLocationThreshold.SetFloat(0.5f);

        MinimumSpacingSeconds.Name = "Minimum Raw Candidate Spacing Seconds";
        MinimumSpacingSeconds.SetInt(900);
        MinimumSpacingSeconds.SetIntLimits(0, 7200);

        MaxRawCandidatesPerDay.Name = "Max Raw Candidates Per Day";
        MaxRawCandidatesPerDay.SetInt(20);
        MaxRawCandidatesPerDay.SetIntLimits(0, 200);

        ContextLookbackBars.Name = "Context Lookback Bars";
        ContextLookbackBars.SetInt(20);
        ContextLookbackBars.SetIntLimits(1, 200);

        MinimumLookbackDirectionalMovePoints.Name = "Maximum Lookback Directional Move Points";
        MinimumLookbackDirectionalMovePoints.SetFloat(-2.5f);

        MinimumSessionRangePoints.Name = "Minimum Session Range Points";
        MinimumSessionRangePoints.SetFloat(30.0f);

        MaxRiskToAverageBarRange.Name = "Max Risk To Average Bar Range";
        MaxRiskToAverageBarRange.SetFloat(1.75f);

        InitialStopPoints.Name = "Initial Stop Points";
        InitialStopPoints.SetFloat(10.0f);

        FirstTargetPoints.Name = "First Target Points";
        FirstTargetPoints.SetFloat(6.0f);

        RunnerTargetPoints.Name = "Runner Target Points";
        RunnerTargetPoints.SetFloat(12.0f);

        FirstLegQuantity.Name = "First Leg Quantity";
        FirstLegQuantity.SetInt(1);
        FirstLegQuantity.SetIntLimits(1, 100);

        RunnerQuantity.Name = "Runner Quantity";
        RunnerQuantity.SetInt(1);
        RunnerQuantity.SetIntLimits(1, 100);

        DailyLossLimitUsd.Name = "Paper Daily Loss Limit USD";
        DailyLossLimitUsd.SetFloat(3600.0f);

        DailyProfitLockUsd.Name = "Paper Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(0.0f);

        MaxAcceptedDrawdownUsd.Name = "Paper Accepted Equity Drawdown USD";
        MaxAcceptedDrawdownUsd.SetFloat(4000.0f);

        PointValueUsd.Name = "Point Value USD";
        PointValueUsd.SetFloat(50.0f);

        TickValueUsd.Name = "Tick Value USD";
        TickValueUsd.SetFloat(12.5f);

        CommissionPerSideUsd.Name = "Commission Per Side USD";
        CommissionPerSideUsd.SetFloat(1.75f);

        SlippageTicksPerContract.Name = "Slippage Ticks Per Contract";
        SlippageTicksPerContract.SetFloat(1.0f);

        MaxOpenPaperTrades.Name = "Max Open Paper Trades";
        MaxOpenPaperTrades.SetInt(20);
        MaxOpenPaperTrades.SetIntLimits(1, 200);

        return;
    }

    if (sc.LastCallToFunction)
    {
        DeleteOpenTrades(sc);
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
    int& full_recalculation_reset_done = sc.GetPersistentInt(5);
    int& processing_initialized = sc.GetPersistentInt(9);
    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        if (full_recalculation_reset_done == 0)
        {
            last_processed_bar_index = -1;
            sc.GetPersistentInt(2) = 0;
            sc.GetPersistentInt(3) = 0;
            sc.GetPersistentInt(4) = -1;
            sc.GetPersistentInt(6) = 0;
            sc.GetPersistentInt(7) = 0;
            sc.GetPersistentInt(8) = 0;
            sc.GetPersistentInt(10) = 0;
            processing_initialized = 1;
            sc.GetPersistentDouble(1) = 0.0;
            sc.GetPersistentDouble(2) = 0.0;
            sc.GetPersistentDouble(3) = 0.0;
            GetOpenTrades(sc)->clear();
            if (ResetCsvOnFullRecalculation.GetYesNo() != 0)
                std::remove(csv_log_path.c_str());
            full_recalculation_reset_done = 1;
        }
    }
    else
    {
        full_recalculation_reset_done = 0;
        if (processing_initialized == 0)
        {
            last_processed_bar_index = latest_closed_bar_index - 1;
            processing_initialized = 1;
        }
        if (latest_closed_bar_index < last_processed_bar_index)
            last_processed_bar_index = latest_closed_bar_index - 1;
    }

    int start_bar_index = latest_closed_bar_index;
    if (ProcessFullRecalculation.GetYesNo() != 0 && sc.IsFullRecalculation)
        start_bar_index = 0;
    else if (latest_closed_bar_index <= last_processed_bar_index)
        return;
    else
        start_bar_index = MaxInt(0, last_processed_bar_index + 1);

    const std::string symbol = ToStdString(sc.Symbol);
    const std::string trade_mode = ToStdString(TradeMode.GetString());
    std::vector<PaperTrade>* open_trades = GetOpenTrades(sc);

    for (int bar_index = start_bar_index; bar_index <= latest_closed_bar_index; ++bar_index)
    {
        if (bar_index <= last_processed_bar_index)
            continue;
        if (sc.GetBarHasClosedStatus(bar_index) != BHCS_BAR_HAS_CLOSED)
            continue;

        EnsureHealthDate(sc, bar_index);
        const std::string timestamp = ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]));
        const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();

        for (std::vector<PaperTrade>::iterator trade = open_trades->begin(); trade != open_trades->end();)
        {
            if (bar_index <= trade->entry_bar_index)
            {
                ++trade;
                continue;
            }

            bool final_exit = false;
            double exit_price = sc.BaseDataIn[SC_LAST][bar_index];
            std::string exit_reason;

            if (trade->leg1_open && trade->runner_open)
            {
                const bool stop_hit = StopHit(*trade, sc, bar_index);
                const bool first_hit = FirstTargetHit(*trade, sc, bar_index);
                if (stop_hit && first_hit)
                {
                    trade->leg1_exit_price = trade->stop_price;
                    trade->runner_exit_price = trade->stop_price;
                    trade->leg1_open = false;
                    trade->runner_open = false;
                    exit_price = trade->stop_price;
                    exit_reason = "ambiguous_full_stop_first";
                    final_exit = true;
                }
                else if (stop_hit)
                {
                    trade->leg1_exit_price = trade->stop_price;
                    trade->runner_exit_price = trade->stop_price;
                    trade->leg1_open = false;
                    trade->runner_open = false;
                    exit_price = trade->stop_price;
                    exit_reason = "full_stop_hit";
                    final_exit = true;
                }
                else if (first_hit)
                {
                    trade->leg1_exit_price = trade->first_target_price;
                    trade->leg1_open = false;
                    AppendBotLogRow(
                        csv_log_path,
                        "paper_leg1_exit",
                        timestamp,
                        symbol,
                        sc.ChartNumber,
                        bar_index,
                        trade_mode,
                        trade->signal_id,
                        trade->trade_id,
                        trade->direction,
                        "paper_leg1_exit",
                        trade->first_target_price,
                        trade->entry_price,
                        trade->stop_price,
                        trade->first_target_price,
                        trade->runner_target_price,
                        "first_target_hit",
                        trade->first_leg_quantity,
                        trade->leg1_open,
                        trade->runner_open,
                        GrossPoints(trade->direction, trade->entry_price, trade->first_target_price)
                            * static_cast<double>(trade->first_leg_quantity),
                        GrossPoints(trade->direction, trade->entry_price, trade->first_target_price)
                            * static_cast<double>(trade->first_leg_quantity)
                            * PointValueUsd.GetFloat(),
                        0.0,
                        0.0,
                        0.0,
                        sc.GetPersistentDouble(1),
                        sc.GetPersistentDouble(2),
                        AcceptedDrawdown(sc),
                        "not_applicable",
                        "first paper contract hit fixed target");
                }
            }

            if (!final_exit && !trade->runner_open)
            {
                final_exit = true;
                exit_reason = trade->final_exit_reason.empty() ? "runner_exit" : trade->final_exit_reason;
                exit_price = trade->runner_exit_price;
            }

            if (!final_exit && !trade->leg1_open && trade->runner_open)
            {
                const bool runner_stop_hit = StopHit(*trade, sc, bar_index);
                const bool runner_target_hit = RunnerTargetHit(*trade, sc, bar_index);
                if (runner_stop_hit && runner_target_hit)
                {
                    trade->runner_exit_price = trade->stop_price;
                    trade->runner_open = false;
                    exit_price = trade->stop_price;
                    exit_reason = "ambiguous_runner_stop_first";
                    final_exit = true;
                }
                else if (runner_stop_hit)
                {
                    trade->runner_exit_price = trade->stop_price;
                    trade->runner_open = false;
                    exit_price = trade->stop_price;
                    exit_reason = "runner_initial_stop_hit";
                    final_exit = true;
                }
                else if (runner_target_hit)
                {
                    trade->runner_exit_price = trade->runner_target_price;
                    trade->runner_open = false;
                    exit_price = trade->runner_target_price;
                    exit_reason = "runner_target_hit";
                    final_exit = true;
                }
            }

            if (!final_exit && bar_time >= FlattenTime.GetTime())
            {
                if (trade->leg1_open)
                {
                    trade->leg1_exit_price = sc.BaseDataIn[SC_LAST][bar_index];
                    trade->leg1_open = false;
                }
                if (trade->runner_open)
                {
                    trade->runner_exit_price = sc.BaseDataIn[SC_LAST][bar_index];
                    trade->runner_open = false;
                }
                exit_price = sc.BaseDataIn[SC_LAST][bar_index];
                exit_reason = "paper_session_flat";
                final_exit = true;
            }

            if (final_exit)
            {
                double gross_points = 0.0;
                double gross_usd = 0.0;
                double commission_usd = 0.0;
                double slippage_usd = 0.0;
                const double net_usd = TradeNetUsd(
                    *trade,
                    PointValueUsd.GetFloat(),
                    TickValueUsd.GetFloat(),
                    CommissionPerSideUsd.GetFloat(),
                    SlippageTicksPerContract.GetFloat(),
                    gross_points,
                    gross_usd,
                    commission_usd,
                    slippage_usd);

                ApplyRealizedHealthUpdate(
                    sc,
                    bar_index,
                    net_usd,
                    DailyLossLimitUsd.GetFloat(),
                    DailyProfitLockUsd.GetFloat(),
                    MaxAcceptedDrawdownUsd.GetFloat());

                AppendBotLogRow(
                    csv_log_path,
                    "paper_exit",
                    timestamp,
                    symbol,
                    sc.ChartNumber,
                    bar_index,
                    trade_mode,
                    trade->signal_id,
                    trade->trade_id,
                    trade->direction,
                    "paper_exit",
                    exit_price,
                    trade->entry_price,
                    trade->stop_price,
                    trade->first_target_price,
                    trade->runner_target_price,
                    exit_reason,
                    trade->first_leg_quantity + trade->runner_quantity,
                    trade->leg1_open,
                    trade->runner_open,
                    gross_points,
                    gross_usd,
                    commission_usd,
                    slippage_usd,
                    net_usd,
                    sc.GetPersistentDouble(1),
                    sc.GetPersistentDouble(2),
                    AcceptedDrawdown(sc),
                    "not_applicable",
                    "paper trade final exit");
                DrawExitMarker(sc, *trade, bar_index, exit_price, "Axon paper exit");
                trade = open_trades->erase(trade);
                continue;
            }

            ++trade;
        }

        SignalCandidate candidate = EvaluateCandidate(
            sc,
            bar_index,
            SetupStartTime.GetTime(),
            SetupEndTime.GetTime(),
            VwapExtensionPoints.GetFloat(),
            DeltaThreshold.GetFloat(),
            CloseLocationThreshold.GetFloat(),
            ContextLookbackBars.GetInt(),
            MinimumLookbackDirectionalMovePoints.GetFloat(),
            MinimumSessionRangePoints.GetFloat(),
            MaxRiskToAverageBarRange.GetFloat(),
            InitialStopPoints.GetFloat(),
            FirstTargetPoints.GetFloat(),
            RunnerTargetPoints.GetFloat());

        const std::string signal_id = SignalId(symbol, bar_index, candidate.direction);
        if (!candidate.has_raw_setup)
        {
            if (LogRejections.GetYesNo() != 0)
                LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        std::string rejection_reason;
        std::string rejection_notes;
        if (!RawPacingAllowed(
                sc,
                bar_index,
                MinimumSpacingSeconds.GetInt(),
                MaxRawCandidatesPerDay.GetInt(),
                rejection_reason,
                rejection_notes))
        {
            candidate.rejection_reason = rejection_reason;
            candidate.notes = rejection_notes;
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }
        RecordRawCandidate(sc, bar_index);

        if (!candidate.accepted)
        {
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (FirstLegQuantity.GetInt() <= 0 || RunnerQuantity.GetInt() <= 0)
        {
            candidate.rejection_reason = "configuration_error";
            candidate.notes = "first leg quantity and runner quantity must both be positive";
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (EnablePaperEntries.GetYesNo() == 0)
        {
            candidate.rejection_reason = "paper_entries_disabled";
            candidate.notes = "Enable Paper Entries is No";
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (static_cast<int>(open_trades->size()) >= MaxOpenPaperTrades.GetInt())
        {
            candidate.rejection_reason = "max_open_paper_trades";
            candidate.notes = "maximum open paper trades reached";
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (!HealthAllowsNewEntry(sc, bar_index, rejection_reason, rejection_notes))
        {
            candidate.rejection_reason = rejection_reason;
            candidate.notes = rejection_notes;
            LogCandidateRejection(sc, csv_log_path, symbol, trade_mode, bar_index, candidate, signal_id);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        int& next_trade_id = sc.GetPersistentInt(8);
        next_trade_id += 1;

        PaperTrade trade;
        trade.trade_id = next_trade_id;
        trade.entry_bar_index = bar_index;
        trade.entry_date = sc.BaseDateTimeIn[bar_index].GetDate();
        trade.signal_id = signal_id;
        trade.direction = candidate.direction;
        trade.entry_price = candidate.entry_price;
        trade.stop_price = candidate.stop_price;
        trade.first_target_price = candidate.first_target_price;
        trade.runner_target_price = candidate.runner_target_price;
        trade.first_leg_quantity = FirstLegQuantity.GetInt();
        trade.runner_quantity = RunnerQuantity.GetInt();
        open_trades->push_back(trade);

        std::ostringstream entry_notes;
        entry_notes << candidate.notes
                    << "; first_leg_quantity=" << trade.first_leg_quantity
                    << "; runner_quantity=" << trade.runner_quantity;

        AppendBotLogRow(
            csv_log_path,
            "paper_entry",
            timestamp,
            symbol,
            sc.ChartNumber,
            bar_index,
            trade_mode,
            signal_id,
            trade.trade_id,
            trade.direction,
            "paper_entry",
            trade.entry_price,
            trade.entry_price,
            trade.stop_price,
            trade.first_target_price,
            trade.runner_target_price,
            "",
            trade.first_leg_quantity + trade.runner_quantity,
            trade.leg1_open,
            trade.runner_open,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            sc.GetPersistentDouble(1),
            sc.GetPersistentDouble(2),
            AcceptedDrawdown(sc),
            "not_applicable",
            entry_notes.str());
        DrawEntryOverlay(sc, trade);
        DrawTradeLevels(sc, trade);

        last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
    }
}
