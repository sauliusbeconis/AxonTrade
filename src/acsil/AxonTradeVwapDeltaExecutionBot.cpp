#include "sierrachart.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

SCDLLName("AxonTrade VWAP Delta Execution Bot")

namespace
{
const char* kStrategyId =
    "vwap_delta_exhaustion_fade_2pt_10d_cl0.5_space300_exit7_12_10_lb15_risk171_open_m80_range100_daily2400_execution";
const char* kRequiredConfirmationText = "SIM_ONLY";
const char* kRequiredLiveEvalConfirmationText = "MES_EVAL_LIVE";
const int kTradeDrawingBase = 7600000;
const int kStatusDrawingLineNumberBase = 9500000;
const int kTrackedOrdersPointerKey = 101;
const int kFillTrackingInitializedKey = 10;
const int kProcessedFillCountKey = 11;
const int kEvalPnlBaselineInitializedKey = 12;
const int kEvalTrailingLockKey = 13;
const int kEvalPnlBaselineDoubleKey = 201;
const int kEvalHighWaterDoubleKey = 202;

enum DailyLockReason
{
    DAILY_LOCK_NONE = 0,
    DAILY_LOCK_LOSS = 1,
    DAILY_LOCK_PROFIT = 2
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
    double session_open_price = 0.0;
    double directional_open_distance_points = 0.0;
    double average_bar_range_points = 0.0;
    double risk_to_average_bar_range = 0.0;
    double lookback_directional_move_points = 0.0;
};

struct TrackedBotOrder
{
    uint32_t internal_order_id = 0;
    int entry_bar_index = 0;
    std::string direction;
    std::string role;
    std::string signal_id;
};

std::string ToStdString(const SCString& value)
{
    return std::string(value.GetChars());
}

int MinInt(int left, int right)
{
    return left < right ? left : right;
}

int MaxInt(int left, int right)
{
    return left > right ? left : right;
}

double MinDouble(double left, double right)
{
    return left < right ? left : right;
}

double MaxDouble(double left, double right)
{
    return left > right ? left : right;
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

bool StartsWith(const std::string& value, const std::string& prefix)
{
    if (prefix.empty())
        return true;
    if (value.size() < prefix.size())
        return false;
    return value.compare(0, prefix.size(), prefix) == 0;
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

double SessionOpenPriceAtBar(SCStudyInterfaceRef sc, int bar_index)
{
    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];
    int first_session_index = bar_index;

    for (int index = bar_index - 1; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;
        first_session_index = index;
    }

    return sc.BaseDataIn[SC_OPEN][first_session_index];
}

double DirectionalOpenDistancePoints(double entry_price, double session_open_price, const std::string& direction)
{
    if (direction == "long")
        return entry_price - session_open_price;
    return session_open_price - entry_price;
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

double DailyLossView(const s_SCPositionData& position_data)
{
    const double trade_stats_view =
        position_data.TradeStatsDailyProfitLoss + position_data.TradeStatsOpenProfitLoss;
    const double daily_with_open_view =
        position_data.DailyProfitLoss + position_data.OpenProfitLoss;
    return MinDouble(position_data.DailyProfitLoss, MinDouble(trade_stats_view, daily_with_open_view));
}

double DailyProfitView(const s_SCPositionData& position_data)
{
    const double trade_stats_view =
        position_data.TradeStatsDailyProfitLoss + position_data.TradeStatsOpenProfitLoss;
    const double daily_with_open_view =
        position_data.DailyProfitLoss + position_data.OpenProfitLoss;
    return MaxDouble(position_data.DailyProfitLoss, MaxDouble(trade_stats_view, daily_with_open_view));
}

double AccountProfitLossView(const s_SCPositionData& position_data)
{
    return position_data.CumulativeProfitLoss + position_data.OpenProfitLoss;
}

void EnsureDailyLockDate(SCStudyInterfaceRef sc, int bar_index)
{
    int& daily_lock_date = sc.GetPersistentInt(7);
    int& daily_lock_reason = sc.GetPersistentInt(8);
    const int current_date = sc.BaseDateTimeIn[bar_index].GetDate();
    if (daily_lock_date != current_date)
    {
        daily_lock_date = current_date;
        daily_lock_reason = DAILY_LOCK_NONE;
    }
}

void ResetEvalTrailingState(SCStudyInterfaceRef sc, const s_SCPositionData& position_data)
{
    sc.GetPersistentDouble(kEvalPnlBaselineDoubleKey) = AccountProfitLossView(position_data);
    sc.GetPersistentDouble(kEvalHighWaterDoubleKey) = 0.0;
    sc.GetPersistentInt(kEvalPnlBaselineInitializedKey) = 1;
    sc.GetPersistentInt(kEvalTrailingLockKey) = 0;
}

void EnsureEvalTrailingState(SCStudyInterfaceRef sc, const s_SCPositionData& position_data)
{
    if (sc.GetPersistentInt(kEvalPnlBaselineInitializedKey) == 0)
        ResetEvalTrailingState(sc, position_data);
}

bool EvalTrailingDrawdownBlocks(
    SCStudyInterfaceRef sc,
    const s_SCPositionData& position_data,
    double max_trailing_drawdown_usd,
    std::string& rejection_reason,
    std::string& notes)
{
    EnsureEvalTrailingState(sc, position_data);

    if (max_trailing_drawdown_usd <= 0.0)
        return false;

    double& high_water = sc.GetPersistentDouble(kEvalHighWaterDoubleKey);
    const double baseline = sc.GetPersistentDouble(kEvalPnlBaselineDoubleKey);
    const double relative_pnl = AccountProfitLossView(position_data) - baseline;
    if (relative_pnl > high_water)
        high_water = relative_pnl;

    const double trailing_floor = MinDouble(0.0, high_water - max_trailing_drawdown_usd);
    if (sc.GetPersistentInt(kEvalTrailingLockKey) != 0 || relative_pnl <= trailing_floor)
    {
        sc.GetPersistentInt(kEvalTrailingLockKey) = 1;
        rejection_reason = "eval_trailing_drawdown_lock";
        std::ostringstream output;
        output << "eval trailing drawdown lock active; relative_pnl="
               << FormatNumber(relative_pnl)
               << "; high_water=" << FormatNumber(high_water)
               << "; floor=" << FormatNumber(trailing_floor)
               << "; max_trailing_drawdown_usd=" << FormatNumber(max_trailing_drawdown_usd);
        notes = output.str();
        return true;
    }
    return false;
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

void AppendExecutionLogRow(
    const std::string& file_path,
    const std::string& event_type,
    const std::string& timestamp,
    const std::string& symbol,
    const std::string& trade_account,
    int chart_number,
    int bar_index,
    const std::string& trade_mode,
    const std::string& signal_id,
    const std::string& direction,
    const std::string& action,
    double price,
    double entry_price,
    double stop_price,
    double first_target_price,
    double runner_target_price,
    int quantity,
    int first_leg_quantity,
    int runner_quantity,
    int order_result,
    uint32_t parent_internal_order_id,
    uint32_t target1_internal_order_id,
    uint32_t target2_internal_order_id,
    uint32_t stop_all_internal_order_id,
    const s_SCPositionData& position_data,
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
        output << "schema_version,event_type,timestamp,symbol,trade_account,chart_number,bar_index,"
               << "trade_mode,strategy_id,signal_id,direction,action,price,entry_price,stop_price,"
               << "first_target_price,runner_target_price,quantity,first_leg_quantity,runner_quantity,"
               << "order_result,parent_internal_order_id,target1_internal_order_id,target2_internal_order_id,"
               << "stop_all_internal_order_id,position_quantity,working_orders_exist,daily_profit_loss,"
               << "trade_stats_daily_profit_loss,trade_stats_open_profit_loss,open_profit_loss,"
               << "daily_loss_view,daily_profit_view,rejection_reason,notes\n";
    }

    output << 1 << ','
           << EscapeCsv(event_type) << ','
           << EscapeCsv(timestamp) << ','
           << EscapeCsv(symbol) << ','
           << EscapeCsv(trade_account) << ','
           << chart_number << ','
           << bar_index << ','
           << EscapeCsv(trade_mode) << ','
           << EscapeCsv(kStrategyId) << ','
           << EscapeCsv(signal_id) << ','
           << EscapeCsv(direction) << ','
           << EscapeCsv(action) << ','
           << FormatNumber(price) << ','
           << FormatNumber(entry_price) << ','
           << FormatNumber(stop_price) << ','
           << FormatNumber(first_target_price) << ','
           << FormatNumber(runner_target_price) << ','
           << quantity << ','
           << first_leg_quantity << ','
           << runner_quantity << ','
           << order_result << ','
           << parent_internal_order_id << ','
           << target1_internal_order_id << ','
           << target2_internal_order_id << ','
           << stop_all_internal_order_id << ','
           << FormatNumber(position_data.PositionQuantity) << ','
           << position_data.WorkingOrdersExist << ','
           << FormatNumber(position_data.DailyProfitLoss) << ','
           << FormatNumber(position_data.TradeStatsDailyProfitLoss) << ','
           << FormatNumber(position_data.TradeStatsOpenProfitLoss) << ','
           << FormatNumber(position_data.OpenProfitLoss) << ','
           << FormatNumber(DailyLossView(position_data)) << ','
           << FormatNumber(DailyProfitView(position_data)) << ','
           << EscapeCsv(rejection_reason) << ','
           << EscapeCsv(notes) << '\n';
}

std::string SignalId(const std::string& symbol, int bar_index, const std::string& direction)
{
    std::ostringstream output;
    output << kStrategyId << '_' << symbol << '_' << bar_index << '_' << direction;
    return output.str();
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
    double minimum_directional_open_distance_points,
    double maximum_session_range_points,
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
    candidate.session_open_price = SessionOpenPriceAtBar(sc, bar_index);
    candidate.directional_open_distance_points = DirectionalOpenDistancePoints(
        close,
        candidate.session_open_price,
        candidate.direction);

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
    if (candidate.directional_open_distance_points < minimum_directional_open_distance_points)
    {
        std::ostringstream notes;
        notes << "directional_open_distance_points="
              << FormatNumber(candidate.directional_open_distance_points)
              << " is below trend-day veto threshold "
              << FormatNumber(minimum_directional_open_distance_points);
        candidate.rejection_reason = "directional_open_distance_guard";
        candidate.notes = notes.str();
        return candidate;
    }
    if (maximum_session_range_points > 0.0 && candidate.session_range_points > maximum_session_range_points)
    {
        std::ostringstream notes;
        notes << "session_range_points=" << FormatNumber(candidate.session_range_points)
              << " is above trend-day veto threshold "
              << FormatNumber(maximum_session_range_points);
        candidate.rejection_reason = "maximum_session_range_guard";
        candidate.notes = notes.str();
        return candidate;
    }

    candidate.accepted = true;
    candidate.action = "execution_entry";
    candidate.rejection_reason = "not_applicable";
    std::ostringstream notes;
    notes << candidate.direction << " VWAP/delta exhaustion fade; "
          << "distance_from_vwap=" << FormatNumber(candidate.distance_from_vwap) << "; "
          << "delta=" << FormatNumber(candidate.delta) << "; "
          << "close_location=" << FormatNumber(candidate.close_location) << "; "
          << "lookback_directional_move_points=" << FormatNumber(candidate.lookback_directional_move_points) << "; "
          << "session_range_points=" << FormatNumber(candidate.session_range_points) << "; "
          << "session_open_price=" << FormatNumber(candidate.session_open_price) << "; "
          << "directional_open_distance_points=" << FormatNumber(candidate.directional_open_distance_points) << "; "
          << "risk_to_average_bar_range=" << FormatNumber(candidate.risk_to_average_bar_range);
    candidate.notes = notes.str();
    return candidate;
}

void LogCandidateEvent(
    SCStudyInterfaceRef sc,
    const std::string& csv_log_path,
    const std::string& event_type,
    const std::string& symbol,
    const std::string& trade_account,
    const std::string& trade_mode,
    int bar_index,
    const SignalCandidate& candidate,
    const std::string& signal_id,
    int quantity,
    int first_leg_quantity,
    int runner_quantity,
    int order_result,
    uint32_t parent_internal_order_id,
    uint32_t target1_internal_order_id,
    uint32_t target2_internal_order_id,
    uint32_t stop_all_internal_order_id,
    const s_SCPositionData& position_data,
    const std::string& rejection_reason,
    const std::string& notes)
{
    AppendExecutionLogRow(
        csv_log_path,
        event_type,
        ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index])),
        symbol,
        trade_account,
        sc.ChartNumber,
        bar_index,
        trade_mode,
        signal_id,
        candidate.direction,
        event_type,
        candidate.entry_price,
        candidate.entry_price,
        candidate.stop_price,
        candidate.first_target_price,
        candidate.runner_target_price,
        quantity,
        first_leg_quantity,
        runner_quantity,
        order_result,
        parent_internal_order_id,
        target1_internal_order_id,
        target2_internal_order_id,
        stop_all_internal_order_id,
        position_data,
        rejection_reason,
        notes);
}

void LogOperationalEvent(
    SCStudyInterfaceRef sc,
    const std::string& csv_log_path,
    const std::string& event_type,
    const std::string& symbol,
    const std::string& trade_account,
    const std::string& trade_mode,
    int bar_index,
    const std::string& action,
    int order_result,
    const s_SCPositionData& position_data,
    const std::string& rejection_reason,
    const std::string& notes)
{
    AppendExecutionLogRow(
        csv_log_path,
        event_type,
        ToStdString(sc.FormatDateTime(sc.BaseDateTimeIn[bar_index])),
        symbol,
        trade_account,
        sc.ChartNumber,
        bar_index,
        trade_mode,
        "",
        "none",
        action,
        sc.BaseDataIn[SC_LAST][bar_index],
        0.0,
        0.0,
        0.0,
        0.0,
        0,
        0,
        0,
        order_result,
        0,
        0,
        0,
        0,
        position_data,
        rejection_reason,
        notes);
}

void AlertAcceptedSetup(
    SCStudyInterfaceRef sc,
    int bar_index,
    const std::string& symbol,
    const SignalCandidate& candidate,
    unsigned int alert_sound_number)
{
    if (alert_sound_number == 0)
        return;
    if (sc.IsFullRecalculation != 0 || sc.DownloadingHistoricalData != 0)
        return;
    if (sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0)
        return;

    SCString message;
    message.Format(
        "AxonTrade accepted setup: %s %s at %s entry=%s",
        symbol.c_str(),
        candidate.direction.c_str(),
        sc.FormatDateTime(sc.BaseDateTimeIn[bar_index]).GetChars(),
        FormatNumber(candidate.entry_price).c_str());
    sc.SetAlert(static_cast<int>(alert_sound_number) - 1, bar_index, message);
}

std::vector<TrackedBotOrder>& TrackedBotOrders(SCStudyInterfaceRef sc)
{
    std::vector<TrackedBotOrder>* tracked_orders =
        static_cast<std::vector<TrackedBotOrder>*>(sc.GetPersistentPointer(kTrackedOrdersPointerKey));
    if (tracked_orders == 0)
    {
        tracked_orders = new std::vector<TrackedBotOrder>();
        sc.SetPersistentPointer(kTrackedOrdersPointerKey, tracked_orders);
    }
    return *tracked_orders;
}

void DeleteTrackedBotOrders(SCStudyInterfaceRef sc)
{
    std::vector<TrackedBotOrder>* tracked_orders =
        static_cast<std::vector<TrackedBotOrder>*>(sc.GetPersistentPointer(kTrackedOrdersPointerKey));
    delete tracked_orders;
    sc.SetPersistentPointer(kTrackedOrdersPointerKey, 0);
}

void EnsureFillTrackingInitialized(SCStudyInterfaceRef sc)
{
    int& fill_tracking_initialized = sc.GetPersistentInt(kFillTrackingInitializedKey);
    int& processed_fill_count = sc.GetPersistentInt(kProcessedFillCountKey);
    if (fill_tracking_initialized == 0)
    {
        processed_fill_count = sc.GetOrderFillArraySize();
        fill_tracking_initialized = 1;
    }
}

void AddTrackedBotOrder(
    SCStudyInterfaceRef sc,
    uint32_t internal_order_id,
    int entry_bar_index,
    const std::string& direction,
    const std::string& role,
    const std::string& signal_id)
{
    if (internal_order_id == 0)
        return;

    std::vector<TrackedBotOrder>& tracked_orders = TrackedBotOrders(sc);
    for (std::vector<TrackedBotOrder>::const_iterator order = tracked_orders.begin();
         order != tracked_orders.end();
         ++order)
    {
        if (order->internal_order_id == internal_order_id)
            return;
    }

    TrackedBotOrder tracked_order;
    tracked_order.internal_order_id = internal_order_id;
    tracked_order.entry_bar_index = entry_bar_index;
    tracked_order.direction = direction;
    tracked_order.role = role;
    tracked_order.signal_id = signal_id;
    tracked_orders.push_back(tracked_order);

    if (tracked_orders.size() > 400)
        tracked_orders.erase(tracked_orders.begin(), tracked_orders.begin() + 100);
}

void TrackSubmittedBotOrders(
    SCStudyInterfaceRef sc,
    const s_SCNewOrder& new_order,
    int entry_bar_index,
    const SignalCandidate& candidate,
    const std::string& signal_id)
{
    AddTrackedBotOrder(sc, new_order.InternalOrderID, entry_bar_index, candidate.direction, "entry", signal_id);
    AddTrackedBotOrder(sc, new_order.Target1InternalOrderID, entry_bar_index, candidate.direction, "target1", signal_id);
    AddTrackedBotOrder(sc, new_order.Target2InternalOrderID, entry_bar_index, candidate.direction, "target2", signal_id);
    AddTrackedBotOrder(sc, new_order.StopAllInternalOrderID, entry_bar_index, candidate.direction, "stop", signal_id);
}

const TrackedBotOrder* FindTrackedBotOrder(SCStudyInterfaceRef sc, uint32_t internal_order_id)
{
    std::vector<TrackedBotOrder>* tracked_orders =
        static_cast<std::vector<TrackedBotOrder>*>(sc.GetPersistentPointer(kTrackedOrdersPointerKey));
    if (tracked_orders == 0)
        return 0;

    for (std::vector<TrackedBotOrder>::const_iterator order = tracked_orders->begin();
         order != tracked_orders->end();
         ++order)
    {
        if (order->internal_order_id == internal_order_id)
            return &(*order);
    }
    return 0;
}

int TradeDrawingBase(int bar_index, const std::string& direction)
{
    const int direction_offset = direction == "long" ? 0 : 250000;
    return kTradeDrawingBase + direction_offset + bar_index * 20;
}

void DrawTradeLevelLine(
    SCStudyInterfaceRef sc,
    int drawing_number,
    int bar_index,
    int forward_bars,
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
    tool.EndIndex = bar_index + MaxInt(1, forward_bars);
    tool.BeginValue = price;
    tool.EndValue = price;
    tool.Color = color;
    tool.LineWidth = line_width;
    tool.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(tool);
}

void DrawSubmittedTradeOverlay(
    SCStudyInterfaceRef sc,
    int bar_index,
    const SignalCandidate& candidate,
    int first_leg_quantity,
    int runner_quantity,
    int forward_bars)
{
    const bool is_long = candidate.direction == "long";
    const int drawing_base = TradeDrawingBase(bar_index, candidate.direction);
    const COLORREF signal_color = is_long ? RGB(0, 180, 255) : RGB(255, 96, 80);
    const double tick_offset = sc.TickSize > 0.0 ? sc.TickSize * 2.0 : 1.0;
    const double marker_price = is_long
        ? sc.BaseDataIn[SC_LOW][bar_index] - tick_offset
        : sc.BaseDataIn[SC_HIGH][bar_index] + tick_offset;

    s_UseTool marker;
    marker.Clear();
    marker.ChartNumber = sc.ChartNumber;
    marker.DrawingType = DRAWING_MARKER;
    marker.LineNumber = drawing_base + 1;
    marker.Region = 0;
    marker.BeginIndex = bar_index;
    marker.BeginValue = marker_price;
    marker.MarkerType = is_long ? MARKER_ARROWUP : MARKER_ARROWDOWN;
    marker.MarkerSize = 8;
    marker.LineWidth = 5;
    marker.Color = signal_color;
    marker.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(marker);

    SCString label_text;
    label_text.Format(
        "AT submitted %s %d+%d\nE %s\nT1 %s  T2 %s\nS %s",
        candidate.direction.c_str(),
        first_leg_quantity,
        runner_quantity,
        FormatNumber(candidate.entry_price).c_str(),
        FormatNumber(candidate.first_target_price).c_str(),
        FormatNumber(candidate.runner_target_price).c_str(),
        FormatNumber(candidate.stop_price).c_str());

    s_UseTool label;
    label.Clear();
    label.ChartNumber = sc.ChartNumber;
    label.DrawingType = DRAWING_TEXT;
    label.LineNumber = drawing_base + 2;
    label.Region = 0;
    label.BeginIndex = bar_index;
    label.BeginValue = marker_price;
    label.Color = signal_color;
    label.FontSize = 8;
    label.FontBold = 1;
    label.TransparentLabelBackground = 1;
    label.Text = label_text;
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);

    DrawTradeLevelLine(sc, drawing_base + 3, bar_index, forward_bars, candidate.entry_price, RGB(235, 235, 235), 1);
    DrawTradeLevelLine(sc, drawing_base + 4, bar_index, forward_bars, candidate.stop_price, RGB(220, 64, 64), 2);
    DrawTradeLevelLine(sc, drawing_base + 5, bar_index, forward_bars, candidate.first_target_price, RGB(64, 180, 255), 1);
    DrawTradeLevelLine(sc, drawing_base + 6, bar_index, forward_bars, candidate.runner_target_price, RGB(64, 220, 120), 2);
}

void DrawOrderFillMarker(
    SCStudyInterfaceRef sc,
    int fill_index,
    int bar_index,
    const s_SCOrderFillData& fill_data,
    const TrackedBotOrder& tracked_order)
{
    if (bar_index < 0 || sc.ArraySize <= 0)
        return;

    const bool is_entry = tracked_order.role == "entry";
    const bool is_long = tracked_order.direction == "long";
    COLORREF fill_color = RGB(255, 205, 64);
    if (is_entry)
        fill_color = is_long ? RGB(0, 180, 255) : RGB(255, 96, 80);
    else if (tracked_order.role == "stop")
        fill_color = RGB(255, 80, 80);
    else if (tracked_order.role == "target2")
        fill_color = RGB(64, 220, 120);
    else if (tracked_order.role == "target1")
        fill_color = RGB(64, 180, 255);

    const int drawing_base = kTradeDrawingBase + 900000 + fill_index * 4;

    s_UseTool marker;
    marker.Clear();
    marker.ChartNumber = sc.ChartNumber;
    marker.DrawingType = DRAWING_MARKER;
    marker.LineNumber = drawing_base + 1;
    marker.Region = 0;
    marker.BeginIndex = bar_index;
    marker.BeginValue = fill_data.FillPrice;
    marker.MarkerType = is_entry ? (is_long ? MARKER_ARROWUP : MARKER_ARROWDOWN) : MARKER_DIAMOND;
    marker.MarkerSize = is_entry ? 7 : 8;
    marker.LineWidth = 4;
    marker.Color = fill_color;
    marker.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(marker);

    SCString label_text;
    label_text.Format(
        "AT fill %s q=%d @ %s",
        tracked_order.role.c_str(),
        static_cast<int>(fill_data.Quantity),
        FormatNumber(fill_data.FillPrice).c_str());

    s_UseTool label;
    label.Clear();
    label.ChartNumber = sc.ChartNumber;
    label.DrawingType = DRAWING_TEXT;
    label.LineNumber = drawing_base + 2;
    label.Region = 0;
    label.BeginIndex = bar_index;
    label.BeginValue = fill_data.FillPrice;
    label.Color = fill_color;
    label.FontSize = 8;
    label.TransparentLabelBackground = 1;
    label.Text = label_text;
    label.AddMethod = UTAM_ADD_OR_ADJUST;
    sc.UseTool(label);
}

void DrawTrackedOrderFills(
    SCStudyInterfaceRef sc,
    const std::string& symbol,
    const std::string& trade_account,
    bool draw_trade_markers_and_levels)
{
    EnsureFillTrackingInitialized(sc);

    int& processed_fill_count = sc.GetPersistentInt(kProcessedFillCountKey);
    const int current_fill_count = sc.GetOrderFillArraySize();
    if (current_fill_count < processed_fill_count)
        processed_fill_count = current_fill_count;

    for (int fill_index = processed_fill_count; fill_index < current_fill_count; ++fill_index)
    {
        s_SCOrderFillData fill_data;
        sc.GetOrderFillEntry(fill_index, fill_data);
        if (ToStdString(fill_data.Symbol) != symbol)
            continue;
        if (!trade_account.empty() && ToStdString(fill_data.TradeAccount) != trade_account)
            continue;

        const TrackedBotOrder* tracked_order = FindTrackedBotOrder(sc, fill_data.InternalOrderID);
        if (tracked_order == 0)
            continue;

        if (draw_trade_markers_and_levels)
        {
            int bar_index = sc.GetContainingIndexForSCDateTime(sc.ChartNumber, fill_data.FillDateTime);
            if (bar_index < 0)
                bar_index = sc.GetNearestMatchForSCDateTime(sc.ChartNumber, fill_data.FillDateTime);
            bar_index = MinInt(sc.ArraySize - 1, MaxInt(0, bar_index));
            DrawOrderFillMarker(sc, fill_index, bar_index, fill_data, *tracked_order);
        }
    }

    processed_fill_count = current_fill_count;
}

std::string YesNoStatus(bool value)
{
    return value ? "Y" : "N";
}

void DeleteStatusBanner(SCStudyInterfaceRef sc, bool live_eval_profile)
{
    const int drawing_number = kStatusDrawingLineNumberBase + (live_eval_profile ? 1 : 2);
    sc.DeleteACSChartDrawing(sc.ChartNumber, TOOL_DELETE_CHARTDRAWING, drawing_number);
}

void DrawStatusBanner(
    SCStudyInterfaceRef sc,
    bool live_eval_profile,
    int latest_closed_bar_index,
    const std::string& headline,
    const std::string& gate_line,
    const std::string& detail_line,
    COLORREF text_color,
    COLORREF background_color,
    int vertical_position,
    int font_size)
{
    if (latest_closed_bar_index < 0 || sc.ArraySize <= 0)
        return;

    SCString status_text;
    status_text.Format(
        "%s\n%s\n%s",
        headline.c_str(),
        gate_line.c_str(),
        detail_line.c_str());

    s_UseTool tool;
    tool.Clear();
    tool.ChartNumber = sc.ChartNumber;
    tool.DrawingType = DRAWING_TEXT;
    tool.LineNumber = kStatusDrawingLineNumberBase + (live_eval_profile ? 1 : 2);
    tool.Region = 0;
    tool.BeginIndex = MinInt(sc.ArraySize - 1, MaxInt(0, latest_closed_bar_index));
    tool.BeginValue = static_cast<float>(MaxInt(5, MinInt(98, vertical_position)));
    tool.UseRelativeVerticalValues = 1;
    tool.Color = text_color;
    tool.FontBackColor = background_color;
    tool.TransparentLabelBackground = 0;
    tool.FontBold = 1;
    tool.FontSize = MaxInt(6, MinInt(24, font_size));
    tool.MultiLineLabel = 1;
    tool.DrawUnderneathMainGraph = 0;
    tool.AddMethod = UTAM_ADD_OR_ADJUST;
    tool.Text = status_text;
    sc.UseTool(tool);
}

bool DailyLockBlocksNewEntry(
    SCStudyInterfaceRef sc,
    int bar_index,
    const s_SCPositionData& position_data,
    double daily_loss_limit_usd,
    double daily_profit_lock_usd,
    std::string& rejection_reason,
    std::string& notes)
{
    EnsureDailyLockDate(sc, bar_index);
    int& daily_lock_reason = sc.GetPersistentInt(8);

    if (daily_lock_reason == DAILY_LOCK_NONE)
    {
        if (daily_loss_limit_usd > 0.0 && DailyLossView(position_data) <= -daily_loss_limit_usd)
            daily_lock_reason = DAILY_LOCK_LOSS;
        else if (daily_profit_lock_usd > 0.0 && DailyProfitView(position_data) >= daily_profit_lock_usd)
            daily_lock_reason = DAILY_LOCK_PROFIT;
    }

    if (daily_lock_reason == DAILY_LOCK_LOSS)
    {
        rejection_reason = "daily_loss_lock_blocked";
        std::ostringstream output;
        output << "daily loss lock active; loss_view=" << FormatNumber(DailyLossView(position_data))
               << "; limit=" << FormatNumber(daily_loss_limit_usd);
        notes = output.str();
        return true;
    }
    if (daily_lock_reason == DAILY_LOCK_PROFIT)
    {
        rejection_reason = "daily_profit_lock_blocked";
        std::ostringstream output;
        output << "daily profit lock active; profit_view=" << FormatNumber(DailyProfitView(position_data))
               << "; lock=" << FormatNumber(daily_profit_lock_usd);
        notes = output.str();
        return true;
    }
    return false;
}

bool FlattenIfNeeded(
    SCStudyInterfaceRef sc,
    const std::string& csv_log_path,
    const std::string& symbol,
    const std::string& trade_account,
    const std::string& trade_mode,
    int bar_index,
    const std::string& action,
    const std::string& notes)
{
    s_SCPositionData position_data;
    sc.GetTradePosition(position_data);

    if (position_data.PositionQuantity == 0.0 && position_data.WorkingOrdersExist == 0)
        return false;

    const int result = sc.FlattenAndCancelAllOrders();
    s_SCPositionData after_position_data;
    sc.GetTradePosition(after_position_data);
    LogOperationalEvent(
        sc,
        csv_log_path,
        "execution_flatten_submitted",
        symbol,
        trade_account,
        trade_mode,
        bar_index,
        action,
        result,
        after_position_data,
        result > 0 ? "not_applicable" : "flatten_order_error",
        notes);

    if (result <= 0)
        sc.AddMessageToLog(sc.GetTradingErrorTextMessage(result), true);
    return result > 0;
}

void RunVwapDeltaExecutionStudy(SCStudyInterfaceRef sc, bool live_eval_profile)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef TradeMode = sc.Input[1];
    SCInputRef ArmExecution = sc.Input[2];
    SCInputRef SendOrdersToTradeService = sc.Input[3];
    SCInputRef RequireTradeSimulationMode = sc.Input[4];
    SCInputRef ConfirmationText = sc.Input[5];
    SCInputRef RequiredSymbolPrefix = sc.Input[6];
    SCInputRef LogRejections = sc.Input[7];
    SCInputRef ProcessFullRecalculation = sc.Input[8];
    SCInputRef ResetCsvOnFullRecalculation = sc.Input[9];
    SCInputRef SetupStartTime = sc.Input[10];
    SCInputRef SetupEndTime = sc.Input[11];
    SCInputRef FlattenTime = sc.Input[12];
    SCInputRef VwapExtensionPoints = sc.Input[13];
    SCInputRef DeltaThreshold = sc.Input[14];
    SCInputRef CloseLocationThreshold = sc.Input[15];
    SCInputRef MinimumSpacingSeconds = sc.Input[16];
    SCInputRef MaxRawCandidatesPerDay = sc.Input[17];
    SCInputRef ContextLookbackBars = sc.Input[18];
    SCInputRef MinimumLookbackDirectionalMovePoints = sc.Input[19];
    SCInputRef MinimumSessionRangePoints = sc.Input[20];
    SCInputRef MaxRiskToAverageBarRange = sc.Input[21];
    SCInputRef InitialStopPoints = sc.Input[22];
    SCInputRef FirstTargetPoints = sc.Input[23];
    SCInputRef RunnerTargetPoints = sc.Input[24];
    SCInputRef FirstLegQuantity = sc.Input[25];
    SCInputRef RunnerQuantity = sc.Input[26];
    SCInputRef MaxPositionQuantity = sc.Input[27];
    SCInputRef DailyLossLimitUsd = sc.Input[28];
    SCInputRef DailyProfitLockUsd = sc.Input[29];
    SCInputRef MoveStopToBreakEvenAfterFirstTarget = sc.Input[30];
    SCInputRef BreakEvenOffsetTicks = sc.Input[31];
    SCInputRef MinimumDirectionalOpenDistancePoints = sc.Input[32];
    SCInputRef MaximumSessionRangePoints = sc.Input[33];
    SCInputRef AcceptedSetupAlertSound = sc.Input[34];
    SCInputRef DrawTradeMarkersAndLevels = sc.Input[35];
    SCInputRef TradeLevelForwardBars = sc.Input[36];
    SCInputRef AllowedTradeAccount = sc.Input[37];
    SCInputRef MaxEvalTrailingDrawdownUsd = sc.Input[38];
    SCInputRef ResetEvalDrawdownTracking = sc.Input[39];
    SCInputRef DrawStatusBannerInput = sc.Input[40];
    SCInputRef StatusBannerVerticalPosition = sc.Input[41];
    SCInputRef StatusBannerFontSize = sc.Input[42];

    if (sc.SetDefaults)
    {
        sc.GraphName = live_eval_profile
            ? "AxonTrade MES Eval Live Bot"
            : "AxonTrade VWAP Delta Execution Bot";
        sc.StudyDescription = live_eval_profile
            ? "Guarded live-capable MES prop-eval execution bot for the AxonTrade VWAP/delta setup."
            : "Simulation-only execution mechanics harness for the AxonTrade VWAP/delta setup. Live trade-service routing is rejected in this build.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        sc.AllowMultipleEntriesInSameDirection = false;
        sc.MaximumPositionAllowed = 2;
        sc.SupportReversals = false;
        sc.SendOrdersToTradeService = false;
        sc.AllowOppositeEntryWithOpposingPositionOrOrders = false;
        sc.SupportAttachedOrdersForTrading = false;
        sc.CancelAllOrdersOnEntriesAndReversals = true;
        sc.AllowEntryWithWorkingOrders = false;
        sc.CancelAllWorkingOrdersOnExit = true;
        sc.AllowOnlyOneTradePerBar = true;
        sc.MaintainTradeStatisticsAndTradesData = true;

        CsvLogPath.Name = "CSV Log Path";
        CsvLogPath.SetString(live_eval_profile
            ? "C:\\SierraChart\\Data\\AxonTrade_MesEvalLiveBot.csv"
            : "C:\\SierraChart\\Data\\AxonTrade_VwapDeltaExecutionBot.csv");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString(live_eval_profile ? "mes_eval_live" : "execution_sim");

        ArmExecution.Name = "Arm Execution";
        ArmExecution.SetYesNo(0);

        SendOrdersToTradeService.Name = "Send Orders To Trade Service";
        SendOrdersToTradeService.SetYesNo(0);

        RequireTradeSimulationMode.Name = live_eval_profile
            ? "Require Trade Simulation Mode Off"
            : "Require Trade Simulation Mode";
        RequireTradeSimulationMode.SetYesNo(1);

        ConfirmationText.Name = "Confirmation Text";
        ConfirmationText.SetString("");

        RequiredSymbolPrefix.Name = "Required Symbol Prefix";
        RequiredSymbolPrefix.SetString(live_eval_profile ? "MES" : "ES");

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

        FlattenTime.Name = "Flatten Time";
        FlattenTime.SetTime(HMS_TIME(16, 40, 0));

        VwapExtensionPoints.Name = "VWAP Extension Points";
        VwapExtensionPoints.SetFloat(2.0f);

        DeltaThreshold.Name = "Minimum Bar Delta";
        DeltaThreshold.SetFloat(10.0f);

        CloseLocationThreshold.Name = "Close Location Threshold";
        CloseLocationThreshold.SetFloat(0.5f);

        MinimumSpacingSeconds.Name = "Minimum Raw Candidate Spacing Seconds";
        MinimumSpacingSeconds.SetInt(300);
        MinimumSpacingSeconds.SetIntLimits(0, 7200);

        MaxRawCandidatesPerDay.Name = "Max Raw Candidates Per Day";
        MaxRawCandidatesPerDay.SetInt(20);
        MaxRawCandidatesPerDay.SetIntLimits(0, 200);

        ContextLookbackBars.Name = "Context Lookback Bars";
        ContextLookbackBars.SetInt(20);
        ContextLookbackBars.SetIntLimits(1, 200);

        MinimumLookbackDirectionalMovePoints.Name = "Maximum Lookback Directional Move Points";
        MinimumLookbackDirectionalMovePoints.SetFloat(-15.0f);

        MinimumSessionRangePoints.Name = "Minimum Session Range Points";
        MinimumSessionRangePoints.SetFloat(30.0f);

        MaxRiskToAverageBarRange.Name = "Max Risk To Average Bar Range";
        MaxRiskToAverageBarRange.SetFloat(1.7142857f);

        InitialStopPoints.Name = "Initial Stop Points";
        InitialStopPoints.SetFloat(12.0f);

        FirstTargetPoints.Name = "First Target Points";
        FirstTargetPoints.SetFloat(7.0f);

        RunnerTargetPoints.Name = "Runner Target Points";
        RunnerTargetPoints.SetFloat(10.0f);

        FirstLegQuantity.Name = "First Leg Quantity";
        FirstLegQuantity.SetInt(1);
        FirstLegQuantity.SetIntLimits(1, 100);

        RunnerQuantity.Name = "Runner Quantity";
        RunnerQuantity.SetInt(1);
        RunnerQuantity.SetIntLimits(1, 100);

        MaxPositionQuantity.Name = "Max Position Quantity";
        MaxPositionQuantity.SetInt(2);
        MaxPositionQuantity.SetIntLimits(1, 100);

        DailyLossLimitUsd.Name = "Daily Loss Lock USD";
        DailyLossLimitUsd.SetFloat(live_eval_profile ? 240.0f : 2400.0f);

        DailyProfitLockUsd.Name = "Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(live_eval_profile ? 650.0f : 0.0f);

        MoveStopToBreakEvenAfterFirstTarget.Name = "Move Stop To Break Even After First Target";
        MoveStopToBreakEvenAfterFirstTarget.SetYesNo(0);

        BreakEvenOffsetTicks.Name = "Break Even Offset Ticks";
        BreakEvenOffsetTicks.SetInt(0);
        BreakEvenOffsetTicks.SetIntLimits(-20, 20);

        MinimumDirectionalOpenDistancePoints.Name = "Minimum Directional Open Distance Points";
        MinimumDirectionalOpenDistancePoints.SetFloat(-80.0f);

        MaximumSessionRangePoints.Name = "Maximum Session Range Points";
        MaximumSessionRangePoints.SetFloat(100.0f);

        AcceptedSetupAlertSound.Name = "Accepted Setup Alert Sound";
        AcceptedSetupAlertSound.SetAlertSoundNumber(1);

        DrawTradeMarkersAndLevels.Name = "Draw Trade Markers And Levels";
        DrawTradeMarkersAndLevels.SetYesNo(1);

        TradeLevelForwardBars.Name = "Trade Level Forward Bars";
        TradeLevelForwardBars.SetInt(24);
        TradeLevelForwardBars.SetIntLimits(1, 500);

        if (live_eval_profile)
        {
            AllowedTradeAccount.Name = "Allowed Trade Account";
            AllowedTradeAccount.SetString("");

            MaxEvalTrailingDrawdownUsd.Name = "Max Eval Trailing Drawdown USD";
            MaxEvalTrailingDrawdownUsd.SetFloat(1000.0f);

            ResetEvalDrawdownTracking.Name = "Reset Eval Drawdown Tracking";
            ResetEvalDrawdownTracking.SetYesNo(0);
        }

        DrawStatusBannerInput.Name = "Draw Status Banner";
        DrawStatusBannerInput.SetYesNo(live_eval_profile ? 1 : 0);

        StatusBannerVerticalPosition.Name = "Status Banner Vertical Position";
        StatusBannerVerticalPosition.SetInt(92);
        StatusBannerVerticalPosition.SetIntLimits(5, 98);

        StatusBannerFontSize.Name = "Status Banner Font Size";
        StatusBannerFontSize.SetInt(10);
        StatusBannerFontSize.SetIntLimits(6, 24);

        return;
    }

    if (sc.LastCallToFunction)
    {
        DeleteStatusBanner(sc, live_eval_profile);
        DeleteTrackedBotOrders(sc);
        return;
    }

    sc.SendOrdersToTradeService = live_eval_profile && SendOrdersToTradeService.GetYesNo() != 0;
    sc.MaximumPositionAllowed = MaxPositionQuantity.GetInt();
    sc.SupportTradingScaleIn = 0;
    sc.SupportTradingScaleOut = 0;

    if (sc.ArraySize <= 1)
        return;

    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    const int latest_closed_bar_index = LatestClosedBarIndex(sc);
    if (latest_closed_bar_index < 0)
        return;

    int& last_processed_bar_index = sc.GetPersistentInt(1);
    int& full_recalculation_reset_done = sc.GetPersistentInt(5);
    int& processing_initialized = sc.GetPersistentInt(6);

    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        if (full_recalculation_reset_done == 0)
        {
            last_processed_bar_index = -1;
            sc.GetPersistentInt(2) = 0;
            sc.GetPersistentInt(3) = 0;
            sc.GetPersistentInt(4) = -1;
            sc.GetPersistentInt(7) = 0;
            sc.GetPersistentInt(8) = DAILY_LOCK_NONE;
            sc.GetPersistentInt(9) = 0;
            processing_initialized = 1;
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
    bool has_new_closed_bar = true;
    if (ProcessFullRecalculation.GetYesNo() != 0 && sc.IsFullRecalculation)
        start_bar_index = 0;
    else if (latest_closed_bar_index <= last_processed_bar_index)
        has_new_closed_bar = false;
    else
        start_bar_index = MaxInt(0, last_processed_bar_index + 1);

    const std::string symbol = ToStdString(sc.Symbol);
    const std::string trade_account = ToStdString(sc.SelectedTradeAccount);
    const std::string trade_mode = ToStdString(TradeMode.GetString());
    const std::string required_symbol_prefix = ToStdString(RequiredSymbolPrefix.GetString());
    const std::string required_confirmation_text = live_eval_profile
        ? kRequiredLiveEvalConfirmationText
        : kRequiredConfirmationText;
    const std::string allowed_trade_account = live_eval_profile
        ? ToStdString(AllowedTradeAccount.GetString())
        : "";
    const int total_quantity = FirstLegQuantity.GetInt() + RunnerQuantity.GetInt();
    const int trade_level_forward_bars = MaxInt(1, TradeLevelForwardBars.GetInt());

    DrawTrackedOrderFills(
        sc,
        symbol,
        trade_account,
        DrawTradeMarkersAndLevels.GetYesNo() != 0);

    s_SCPositionData immediate_position_data;
    sc.GetTradePosition(immediate_position_data);

    if (live_eval_profile)
    {
        if (ResetEvalDrawdownTracking.GetYesNo() != 0)
        {
            ResetEvalTrailingState(sc, immediate_position_data);
            ResetEvalDrawdownTracking.SetYesNo(0);
            sc.AddMessageToLog("AxonTrade MES eval drawdown tracking reset to current account P/L view.", false);
        }
        else
        {
            EnsureEvalTrailingState(sc, immediate_position_data);
        }
    }

    const bool current_chart_downloading_historical_data =
        sc.DownloadingHistoricalData != 0
        || sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0;
    const bool confirmation_ok = ToStdString(ConfirmationText.GetString()) == required_confirmation_text;
    const bool symbol_ok = StartsWith(symbol, required_symbol_prefix);
    const bool simulation_mode_ok = live_eval_profile
        ? (RequireTradeSimulationMode.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0)
        : (RequireTradeSimulationMode.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0);
    const bool route_ok = live_eval_profile
        ? SendOrdersToTradeService.GetYesNo() != 0
        : SendOrdersToTradeService.GetYesNo() == 0;
    const bool account_ok = !live_eval_profile
        || (!allowed_trade_account.empty() && trade_account == allowed_trade_account);
    const bool live_operational_controls_allowed =
        live_eval_profile
        && ArmExecution.GetYesNo() != 0
        && !csv_log_path.empty()
        && route_ok
        && confirmation_ok
        && simulation_mode_ok
        && account_ok
        && symbol_ok
        && !current_chart_downloading_historical_data;

    bool daily_lock_active = false;
    bool eval_lock_active = false;
    if (live_operational_controls_allowed)
    {
        std::string risk_rejection_reason;
        std::string risk_rejection_notes;
        daily_lock_active = DailyLockBlocksNewEntry(
                sc,
                latest_closed_bar_index,
                immediate_position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                risk_rejection_reason,
                risk_rejection_notes);
        if (daily_lock_active)
        {
            FlattenIfNeeded(
                sc,
                csv_log_path,
                symbol,
                trade_account,
                trade_mode,
                latest_closed_bar_index,
                "daily_lock_flatten",
                risk_rejection_notes);
            sc.GetTradePosition(immediate_position_data);
        }

        eval_lock_active = EvalTrailingDrawdownBlocks(
                sc,
                immediate_position_data,
                MaxEvalTrailingDrawdownUsd.GetFloat(),
                risk_rejection_reason,
                risk_rejection_notes);
        if (eval_lock_active)
        {
            FlattenIfNeeded(
                sc,
                csv_log_path,
                symbol,
                trade_account,
                trade_mode,
                latest_closed_bar_index,
                "eval_trailing_drawdown_flatten",
                risk_rejection_notes);
        }
    }

    sc.GetTradePosition(immediate_position_data);

    if (DrawStatusBannerInput.GetYesNo() != 0)
    {
        std::string headline;
        COLORREF text_color = RGB(255, 255, 255);
        COLORREF background_color = RGB(96, 72, 0);

        if (live_eval_profile)
        {
            if (ArmExecution.GetYesNo() == 0)
            {
                headline = "AXON MES LIVE: STANDBY - NOT ARMED";
                background_color = RGB(96, 72, 0);
            }
            else if (csv_log_path.empty())
            {
                headline = "AXON MES LIVE: BLOCKED - CSV PATH BLANK";
                background_color = RGB(128, 32, 24);
            }
            else if (!route_ok)
            {
                headline = "AXON MES LIVE: BLOCKED - ROUTING OFF";
                background_color = RGB(128, 32, 24);
            }
            else if (!simulation_mode_ok)
            {
                headline = "AXON MES LIVE: BLOCKED - SIERRA SIM MODE IS ON";
                background_color = RGB(128, 32, 24);
            }
            else if (!confirmation_ok)
            {
                headline = "AXON MES LIVE: BLOCKED - CONFIRMATION TEXT";
                background_color = RGB(128, 32, 24);
            }
            else if (allowed_trade_account.empty())
            {
                headline = "AXON MES LIVE: BLOCKED - ALLOWED ACCOUNT BLANK";
                background_color = RGB(128, 32, 24);
            }
            else if (!account_ok)
            {
                headline = "AXON MES LIVE: BLOCKED - ACCOUNT MISMATCH";
                background_color = RGB(128, 32, 24);
            }
            else if (!symbol_ok)
            {
                headline = "AXON MES LIVE: BLOCKED - SYMBOL PREFIX";
                background_color = RGB(128, 32, 24);
            }
            else if (current_chart_downloading_historical_data)
            {
                headline = "AXON MES LIVE: WAIT - HISTORICAL DOWNLOAD";
                background_color = RGB(96, 72, 0);
            }
            else if (daily_lock_active)
            {
                headline = "AXON MES LIVE: LOCKED - DAILY RISK";
                background_color = RGB(128, 32, 24);
            }
            else if (eval_lock_active)
            {
                headline = "AXON MES LIVE: LOCKED - EVAL DRAWDOWN";
                background_color = RGB(128, 32, 24);
            }
            else if (immediate_position_data.PositionQuantity != 0.0 || immediate_position_data.WorkingOrdersExist != 0)
            {
                headline = "AXON MES LIVE: ARMED - MANAGING POSITION/ORDERS";
                background_color = RGB(0, 92, 72);
            }
            else
            {
                headline = "AXON MES LIVE: ARMED - READY FOR LIVE ORDERS";
                background_color = RGB(0, 96, 32);
            }
        }
        else
        {
            headline = ArmExecution.GetYesNo() != 0
                ? "AXON ES SIM BOT: ARMED"
                : "AXON ES SIM BOT: STANDBY";
            background_color = ArmExecution.GetYesNo() != 0 ? RGB(0, 72, 96) : RGB(72, 72, 72);
        }

        std::ostringstream gate_line;
        gate_line << "Gates: arm=" << YesNoStatus(ArmExecution.GetYesNo() != 0)
                  << " route=" << YesNoStatus(route_ok)
                  << " sim=" << (sc.GlobalTradeSimulationIsOn != 0 ? "ON" : "OFF")
                  << " simGate=" << YesNoStatus(simulation_mode_ok)
                  << " confirm=" << YesNoStatus(confirmation_ok)
                  << " acct=" << YesNoStatus(account_ok)
                  << " symbol=" << YesNoStatus(symbol_ok)
                  << " data=" << (current_chart_downloading_historical_data ? "DL" : "OK")
                  << " csv=" << YesNoStatus(!csv_log_path.empty())
                  << " locks=" << (daily_lock_active || eval_lock_active ? "ON" : "OK");

        std::ostringstream detail_line;
        detail_line << "Acct=" << (trade_account.empty() ? "<none>" : trade_account)
                    << " Sym=" << symbol
                    << " Pos=" << FormatNumber(immediate_position_data.PositionQuantity)
                    << " Wkg=" << immediate_position_data.WorkingOrdersExist
                    << " DPL=" << FormatNumber(DailyProfitView(immediate_position_data));
        if (csv_log_path.empty())
            detail_line << " CSV=<blank>";

        DrawStatusBanner(
            sc,
            live_eval_profile,
            latest_closed_bar_index,
            headline,
            gate_line.str(),
            detail_line.str(),
            text_color,
            background_color,
            StatusBannerVerticalPosition.GetInt(),
            StatusBannerFontSize.GetInt());
    }
    else
    {
        DeleteStatusBanner(sc, live_eval_profile);
    }

    if (csv_log_path.empty())
        return;

    if (!has_new_closed_bar)
        return;

    for (int bar_index = start_bar_index; bar_index <= latest_closed_bar_index; ++bar_index)
    {
        if (bar_index <= last_processed_bar_index)
            continue;
        if (sc.GetBarHasClosedStatus(bar_index) != BHCS_BAR_HAS_CLOSED)
            continue;

        EnsureDailyLockDate(sc, bar_index);

        s_SCPositionData position_data;
        sc.GetTradePosition(position_data);

        const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
        const int current_date = sc.BaseDateTimeIn[bar_index].GetDate();
        const bool chart_downloading_historical_data =
            sc.DownloadingHistoricalData != 0
            || sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0;
        const bool order_functions_allowed = live_eval_profile
            ? (
                ArmExecution.GetYesNo() != 0
                && SendOrdersToTradeService.GetYesNo() != 0
                && ToStdString(ConfirmationText.GetString()) == required_confirmation_text
                && (RequireTradeSimulationMode.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0)
                && !allowed_trade_account.empty()
                && trade_account == allowed_trade_account
                && StartsWith(symbol, required_symbol_prefix)
                && !chart_downloading_historical_data)
            : (
                SendOrdersToTradeService.GetYesNo() == 0
                && (RequireTradeSimulationMode.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0)
                && !chart_downloading_historical_data);
        int& flatten_date = sc.GetPersistentInt(9);
        if (order_functions_allowed && bar_time >= FlattenTime.GetTime() && flatten_date != current_date)
        {
            FlattenIfNeeded(
                sc,
                csv_log_path,
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                "session_flatten",
                "flatten time reached");
            flatten_date = current_date;
            sc.GetTradePosition(position_data);
        }

        std::string rejection_reason;
        std::string rejection_notes;
        if (DailyLockBlocksNewEntry(
                sc,
                bar_index,
                position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            if (order_functions_allowed)
            {
                FlattenIfNeeded(
                    sc,
                    csv_log_path,
                    symbol,
                    trade_account,
                    trade_mode,
                    bar_index,
                    "daily_lock_flatten",
                    rejection_notes);
                sc.GetTradePosition(position_data);
            }
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
            MinimumDirectionalOpenDistancePoints.GetFloat(),
            MaximumSessionRangePoints.GetFloat(),
            InitialStopPoints.GetFloat(),
            FirstTargetPoints.GetFloat(),
            RunnerTargetPoints.GetFloat());

        const std::string signal_id = SignalId(symbol, bar_index, candidate.direction);
        if (!candidate.has_raw_setup)
        {
            if (LogRejections.GetYesNo() != 0)
            {
                LogCandidateEvent(
                    sc,
                    csv_log_path,
                    "execution_signal_rejected",
                    symbol,
                    trade_account,
                    trade_mode,
                    bar_index,
                    candidate,
                    signal_id,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    position_data,
                    candidate.rejection_reason,
                    candidate.notes);
            }
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

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
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_signal_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                position_data,
                candidate.rejection_reason,
                candidate.notes);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }
        RecordRawCandidate(sc, bar_index);

        if (!candidate.accepted)
        {
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_signal_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                position_data,
                candidate.rejection_reason,
                candidate.notes);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (ArmExecution.GetYesNo() == 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "execution_not_armed",
                "Arm Execution is No");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (ToStdString(ConfirmationText.GetString()) != required_confirmation_text)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "confirmation_text_missing",
                live_eval_profile
                    ? "Confirmation Text must be MES_EVAL_LIVE"
                    : "Confirmation Text must be SIM_ONLY");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (!live_eval_profile && SendOrdersToTradeService.GetYesNo() != 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "live_trade_service_disabled_in_this_build",
                "Send Orders To Trade Service must remain No in this simulation-only build");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (live_eval_profile && SendOrdersToTradeService.GetYesNo() == 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "live_trade_service_not_enabled",
                "Send Orders To Trade Service must be Yes for the MES eval live bot");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (!live_eval_profile && RequireTradeSimulationMode.GetYesNo() != 0 && sc.GlobalTradeSimulationIsOn == 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "trade_simulation_mode_required",
                "Trade >> Trade Simulation Mode On is not enabled");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (live_eval_profile && RequireTradeSimulationMode.GetYesNo() != 0 && sc.GlobalTradeSimulationIsOn != 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "trade_simulation_mode_must_be_off",
                "Trade >> Trade Simulation Mode On must be off for the MES eval live bot");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (live_eval_profile && allowed_trade_account.empty())
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "allowed_trade_account_missing",
                "Allowed Trade Account must exactly match the selected trade account");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (live_eval_profile && trade_account != allowed_trade_account)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            std::ostringstream notes;
            notes << "selected trade account " << trade_account
                  << " does not match allowed account " << allowed_trade_account;
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "trade_account_gate",
                notes.str());
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (chart_downloading_historical_data)
        {
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "historical_download_in_progress",
                "chart is downloading historical data; entry submission skipped");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (!StartsWith(symbol, required_symbol_prefix))
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            std::ostringstream notes;
            notes << "chart symbol " << symbol << " does not start with required prefix "
                  << required_symbol_prefix;
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "symbol_prefix_gate",
                notes.str());
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (FirstLegQuantity.GetInt() <= 0 || RunnerQuantity.GetInt() <= 0 || total_quantity <= 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "configuration_error",
                "first leg quantity and runner quantity must both be positive");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (total_quantity > MaxPositionQuantity.GetInt())
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "max_position_quantity_gate",
                "first leg plus runner quantity exceeds Max Position Quantity");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (DailyLockBlocksNewEntry(
                sc,
                bar_index,
                position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                rejection_reason,
                rejection_notes);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (live_eval_profile && EvalTrailingDrawdownBlocks(
                sc,
                position_data,
                MaxEvalTrailingDrawdownUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                rejection_reason,
                rejection_notes);
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        if (position_data.PositionQuantity != 0.0 || position_data.WorkingOrdersExist != 0)
        {
            AlertAcceptedSetup(
                sc,
                bar_index,
                symbol,
                candidate,
                AcceptedSetupAlertSound.GetAlertSoundNumber());
            LogCandidateEvent(
                sc,
                csv_log_path,
                "execution_entry_rejected",
                symbol,
                trade_account,
                trade_mode,
                bar_index,
                candidate,
                signal_id,
                total_quantity,
                FirstLegQuantity.GetInt(),
                RunnerQuantity.GetInt(),
                0,
                0,
                0,
                0,
                0,
                position_data,
                "position_or_working_orders_gate",
                "existing position or working orders are present");
            last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
            continue;
        }

        AlertAcceptedSetup(
            sc,
            bar_index,
            symbol,
            candidate,
            AcceptedSetupAlertSound.GetAlertSoundNumber());

        s_SCNewOrder new_order;
        new_order.OrderQuantity = total_quantity;
        new_order.OrderType = SCT_ORDERTYPE_MARKET;
        new_order.TimeInForce = SCT_TIF_GOOD_TILL_CANCELED;
        new_order.TextTag = signal_id.c_str();

        new_order.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
        new_order.Target1Offset = FirstTargetPoints.GetFloat();
        new_order.OCOGroup1Quantity = FirstLegQuantity.GetInt();

        new_order.AttachedOrderTarget2Type = SCT_ORDERTYPE_LIMIT;
        new_order.Target2Offset = RunnerTargetPoints.GetFloat();
        new_order.OCOGroup2Quantity = RunnerQuantity.GetInt();

        new_order.AttachedOrderStopAllType = SCT_ORDERTYPE_STOP;
        new_order.StopAllOffset = InitialStopPoints.GetFloat();

        if (MoveStopToBreakEvenAfterFirstTarget.GetYesNo() != 0)
        {
            new_order.MoveToBreakEven.Type = MOVETO_BE_ACTION_TYPE_OCO_GROUP_TRIGGERED;
            new_order.MoveToBreakEven.BreakEvenLevelOffsetInTicks = BreakEvenOffsetTicks.GetInt();
            new_order.MoveToBreakEven.TriggerOCOGroup = OCO_GROUP_1;
        }

        int order_result = 0;
        if (candidate.direction == "long")
            order_result = static_cast<int>(sc.BuyEntry(new_order, bar_index));
        else
            order_result = static_cast<int>(sc.SellEntry(new_order, bar_index));

        s_SCPositionData after_position_data;
        sc.GetTradePosition(after_position_data);

        if (order_result <= 0)
            sc.AddMessageToLog(sc.GetTradingErrorTextMessage(order_result), true);
        else
        {
            TrackSubmittedBotOrders(sc, new_order, bar_index, candidate, signal_id);
            if (DrawTradeMarkersAndLevels.GetYesNo() != 0)
            {
                DrawSubmittedTradeOverlay(
                    sc,
                    bar_index,
                    candidate,
                    FirstLegQuantity.GetInt(),
                    RunnerQuantity.GetInt(),
                    trade_level_forward_bars);
            }
            DrawTrackedOrderFills(
                sc,
                symbol,
                trade_account,
                DrawTradeMarkersAndLevels.GetYesNo() != 0);
        }

        std::ostringstream entry_notes;
        entry_notes << candidate.notes
                    << "; first_leg_quantity=" << FirstLegQuantity.GetInt()
                    << "; runner_quantity=" << RunnerQuantity.GetInt()
                    << "; stop_all_offset_points=" << FormatNumber(InitialStopPoints.GetFloat())
                    << "; target1_offset_points=" << FormatNumber(FirstTargetPoints.GetFloat())
                    << "; target2_offset_points=" << FormatNumber(RunnerTargetPoints.GetFloat())
                    << "; move_to_breakeven_after_target1="
                    << FormatBool(MoveStopToBreakEvenAfterFirstTarget.GetYesNo() != 0);

        LogCandidateEvent(
            sc,
            csv_log_path,
            order_result > 0 ? "execution_entry_submitted" : "execution_entry_error",
            symbol,
            trade_account,
            trade_mode,
            bar_index,
            candidate,
            signal_id,
            total_quantity,
            FirstLegQuantity.GetInt(),
            RunnerQuantity.GetInt(),
            order_result,
            new_order.InternalOrderID,
            new_order.Target1InternalOrderID,
            new_order.Target2InternalOrderID,
            new_order.StopAllInternalOrderID,
            after_position_data,
            order_result > 0 ? "not_applicable" : "order_submission_error",
            order_result > 0 ? entry_notes.str() : std::string(sc.GetTradingErrorTextMessage(order_result)));

        last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
    }
}

} // namespace

SCSFExport scsf_AxonTradeVwapDeltaExecutionBot(SCStudyInterfaceRef sc)
{
    RunVwapDeltaExecutionStudy(sc, false);
}

SCSFExport scsf_AxonTradeVwapDeltaMesEvalLiveBot(SCStudyInterfaceRef sc)
{
    RunVwapDeltaExecutionStudy(sc, true);
}
