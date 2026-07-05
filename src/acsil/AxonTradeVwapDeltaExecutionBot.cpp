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
const char* kMnqEvalStrategyId =
    "mnq_vwap_delta_local_fade_80pt_400d_cl0.4_nofri_no11_15_exit25_140_40_initial";
const char* kMnqEvalPassCombinedStrategyId =
    "mnq_eval_pass_ab_earliest_one_per_day_fast_aplus12_bfast4";
const char* kMgcNormalBreakEvenStrategyId =
    "mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20";
const char* kMnqTopRunnerStrategyId =
    "mnq_top_runner_lb20_buf0_delta600_cl90_end1100_skipfri_t160_s70";
const char* kRequiredConfirmationText = "SIM_ONLY";
const char* kRequiredLiveEvalConfirmationText = "MES_EVAL_LIVE";
const char* kRequiredMnqEvalConfirmationText = "MNQ_EVAL_LIVE";
const char* kRequiredMnqEvalPassCombinedConfirmationText = "MNQ_EVAL_PASS_AB_LIVE";
const char* kRequiredMgcNormalSimConfirmationText = "MGC_NORMAL_SIM";
const char* kRequiredMgcNormalLiveConfirmationText = "MGC_NORMAL_LIVE";
const char* kRequiredMnqTopRunnerSimConfirmationText = "MNQ_TOP_RUNNER_SIM";
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

const char* StrategyIdForTradeMode(const std::string& trade_mode)
{
    if (trade_mode == "mnq_eval_pass_ab_live")
        return kMnqEvalPassCombinedStrategyId;
    if (trade_mode == "mnq_eval_live")
        return kMnqEvalStrategyId;
    if (trade_mode == "mgc_normal_sim" || trade_mode == "mgc_normal_live")
        return kMgcNormalBreakEvenStrategyId;
    if (trade_mode == "mnq_top_runner_sim")
        return kMnqTopRunnerStrategyId;
    return kStrategyId;
}

bool SameChartDate(const SCDateTime& left, const SCDateTime& right)
{
    return left.GetDate() == right.GetDate();
}

bool EntryScheduleAllowed(
    SCStudyInterfaceRef sc,
    int bar_index,
    bool skip_friday_entries,
    bool skip_eleven_hour_entries,
    bool skip_fifteen_hour_entries,
    std::string& rejection_reason,
    std::string& notes)
{
    const SCDateTime bar_date_time = sc.BaseDateTimeIn[bar_index];
    const int day_of_week = bar_date_time.GetDayOfWeek();
    const int hour = bar_date_time.GetTimeInSeconds() / 3600;

    if (skip_friday_entries && day_of_week == FRIDAY)
    {
        rejection_reason = "schedule_filter_friday";
        notes = "Friday entries are disabled for this profile";
        return false;
    }
    if (skip_eleven_hour_entries && hour == 11)
    {
        rejection_reason = "schedule_filter_11_hour";
        notes = "11:00 exchange-time hour entries are disabled for this profile";
        return false;
    }
    if (skip_fifteen_hour_entries && hour == 15)
    {
        rejection_reason = "schedule_filter_15_hour";
        notes = "15:00 exchange-time hour entries are disabled for this profile";
        return false;
    }
    return true;
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
           << EscapeCsv(StrategyIdForTradeMode(trade_mode)) << ','
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

std::string SignalId(
    const std::string& trade_mode,
    const std::string& symbol,
    int bar_index,
    const std::string& direction)
{
    std::ostringstream output;
    output << StrategyIdForTradeMode(trade_mode) << '_' << symbol << '_' << bar_index << '_' << direction;
    return output.str();
}

SignalCandidate EvaluateCandidate(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    bool skip_friday_entries,
    bool skip_eleven_hour_entries,
    bool skip_fifteen_hour_entries,
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

    if (!EntryScheduleAllowed(
            sc,
            bar_index,
            skip_friday_entries,
            skip_eleven_hour_entries,
            skip_fifteen_hour_entries,
            candidate.rejection_reason,
            candidate.notes))
    {
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

bool PreviousLookbackHighLow(
    SCStudyInterfaceRef sc,
    int bar_index,
    int lookback_bars,
    double& lookback_high,
    double& lookback_low)
{
    if (lookback_bars <= 0 || bar_index <= 0)
        return false;

    const SCDateTime current_date_time = sc.BaseDateTimeIn[bar_index];
    int bars_found = 0;
    for (int index = bar_index - 1; index >= 0; --index)
    {
        if (!SameChartDate(sc.BaseDateTimeIn[index], current_date_time))
            break;

        if (bars_found == 0)
        {
            lookback_high = sc.BaseDataIn[SC_HIGH][index];
            lookback_low = sc.BaseDataIn[SC_LOW][index];
        }
        else
        {
            lookback_high = MaxDouble(lookback_high, sc.BaseDataIn[SC_HIGH][index]);
            lookback_low = MinDouble(lookback_low, sc.BaseDataIn[SC_LOW][index]);
        }

        ++bars_found;
        if (bars_found >= lookback_bars)
            return true;
    }

    return false;
}

SignalCandidate EvaluateLookbackBreakoutCandidate(
    SCStudyInterfaceRef sc,
    int bar_index,
    const std::string& module_name,
    int setup_start_time,
    int setup_end_time,
    int lookback_bars,
    double buffer_points,
    double delta_threshold,
    double close_location_threshold,
    bool short_only,
    bool tuesday_wednesday_only,
    double max_abs_delta,
    double stop_points,
    double target_points)
{
    SignalCandidate candidate;
    const double close = sc.BaseDataIn[SC_LAST][bar_index];
    const int bar_time = sc.BaseDateTimeIn[bar_index].GetTimeInSeconds();
    candidate.entry_price = close;

    if (bar_time < setup_start_time || bar_time > setup_end_time)
    {
        candidate.rejection_reason = "outside_setup_window";
        candidate.notes = module_name + " closed bar is outside setup window";
        return candidate;
    }

    const int day_of_week = sc.BaseDateTimeIn[bar_index].GetDayOfWeek();
    if (tuesday_wednesday_only && day_of_week != TUESDAY && day_of_week != WEDNESDAY)
    {
        candidate.rejection_reason = "weekday_filter";
        candidate.notes = module_name + " is Tuesday/Wednesday only";
        return candidate;
    }

    if (stop_points <= 0.0 || target_points <= 0.0)
    {
        candidate.rejection_reason = "configuration_error";
        candidate.notes = module_name + " has invalid fixed exit points";
        return candidate;
    }

    double lookback_high = 0.0;
    double lookback_low = 0.0;
    if (!PreviousLookbackHighLow(sc, bar_index, lookback_bars, lookback_high, lookback_low))
    {
        candidate.rejection_reason = "insufficient_context";
        candidate.notes = module_name + " does not have enough same-date lookback bars";
        return candidate;
    }

    const double previous_close = sc.BaseDataIn[SC_LAST][bar_index - 1];
    const double high_break = lookback_high + buffer_points;
    const double low_break = lookback_low - buffer_points;
    candidate.vwap = SessionVwapAtBar(sc, bar_index);
    candidate.distance_from_vwap = close - candidate.vwap;
    candidate.delta = BarDelta(sc, bar_index);
    candidate.close_location = CloseLocation(sc, bar_index);

    const bool long_breakout =
        !short_only
        && previous_close <= high_break
        && high_break < close
        && close >= candidate.vwap
        && candidate.delta >= delta_threshold
        && candidate.close_location >= close_location_threshold;
    const bool short_breakout =
        previous_close >= low_break
        && low_break > close
        && close <= candidate.vwap
        && candidate.delta <= -delta_threshold
        && candidate.close_location <= 1.0 - close_location_threshold;

    if (long_breakout)
    {
        candidate.has_raw_setup = true;
        candidate.direction = "long";
    }
    else if (short_breakout)
    {
        candidate.has_raw_setup = true;
        candidate.direction = "short";
    }
    else
    {
        std::ostringstream notes;
        notes << module_name
              << " thresholds not met; previous_close=" << FormatNumber(previous_close)
              << "; high_break=" << FormatNumber(high_break)
              << "; low_break=" << FormatNumber(low_break)
              << "; close=" << FormatNumber(close)
              << "; vwap=" << FormatNumber(candidate.vwap)
              << "; delta=" << FormatNumber(candidate.delta)
              << "; close_location=" << FormatNumber(candidate.close_location);
        candidate.notes = notes.str();
        return candidate;
    }

    const double abs_delta = std::fabs(candidate.delta);
    if (max_abs_delta > 0.0 && abs_delta > max_abs_delta)
    {
        candidate.rejection_reason = "absolute_delta_filter";
        std::ostringstream notes;
        notes << module_name << " raw setup rejected by abs delta cap; abs_delta="
              << FormatNumber(abs_delta) << "; cap=" << FormatNumber(max_abs_delta);
        candidate.notes = notes.str();
        return candidate;
    }

    const bool is_long = candidate.direction == "long";
    candidate.stop_price = is_long ? close - stop_points : close + stop_points;
    candidate.first_target_price = is_long ? close + target_points : close - target_points;
    candidate.runner_target_price = candidate.first_target_price;
    candidate.session_range_points = SessionRangeAtBar(sc, bar_index);
    candidate.session_open_price = SessionOpenPriceAtBar(sc, bar_index);
    candidate.directional_open_distance_points = DirectionalOpenDistancePoints(
        close,
        candidate.session_open_price,
        candidate.direction);

    candidate.accepted = true;
    candidate.action = "execution_entry";
    candidate.rejection_reason = "not_applicable";
    std::ostringstream notes;
    notes << module_name << " " << candidate.direction << " lookback breakout; "
          << "lookback_bars=" << lookback_bars << "; "
          << "buffer_points=" << FormatNumber(buffer_points) << "; "
          << "previous_close=" << FormatNumber(previous_close) << "; "
          << "lookback_high=" << FormatNumber(lookback_high) << "; "
          << "lookback_low=" << FormatNumber(lookback_low) << "; "
          << "high_break=" << FormatNumber(high_break) << "; "
          << "low_break=" << FormatNumber(low_break) << "; "
          << "delta=" << FormatNumber(candidate.delta) << "; "
          << "close_location=" << FormatNumber(candidate.close_location) << "; "
          << "vwap=" << FormatNumber(candidate.vwap) << "; "
          << "distance_from_vwap=" << FormatNumber(candidate.distance_from_vwap) << "; "
          << "target_points=" << FormatNumber(target_points) << "; "
          << "stop_points=" << FormatNumber(stop_points);
    candidate.notes = notes.str();
    return candidate;
}

SignalCandidate EvaluateMgcNormalBreakEvenCandidate(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    int lookback_bars,
    double buffer_points,
    double delta_threshold,
    double close_location_threshold,
    double max_abs_delta,
    double stop_points,
    double target_points)
{
    SignalCandidate candidate;
    candidate.entry_price = sc.BaseDataIn[SC_LAST][bar_index];

    const int day_of_week = sc.BaseDateTimeIn[bar_index].GetDayOfWeek();
    if (day_of_week != MONDAY && day_of_week != TUESDAY && day_of_week != FRIDAY)
    {
        candidate.rejection_reason = "weekday_filter";
        candidate.notes = "MGC_NORMAL only trades Monday/Tuesday/Friday";
        return candidate;
    }

    return EvaluateLookbackBreakoutCandidate(
        sc,
        bar_index,
        "MGC_NORMAL",
        setup_start_time,
        setup_end_time,
        lookback_bars,
        buffer_points,
        delta_threshold,
        close_location_threshold,
        false,
        false,
        max_abs_delta,
        stop_points,
        target_points);
}

SignalCandidate EvaluateMnqTopRunnerCandidate(
    SCStudyInterfaceRef sc,
    int bar_index,
    int setup_start_time,
    int setup_end_time,
    int lookback_bars,
    double buffer_points,
    double delta_threshold,
    double close_location_threshold,
    double stop_points,
    double target_points)
{
    SignalCandidate candidate;
    candidate.entry_price = sc.BaseDataIn[SC_LAST][bar_index];

    const int day_of_week = sc.BaseDateTimeIn[bar_index].GetDayOfWeek();
    if (day_of_week == FRIDAY)
    {
        candidate.rejection_reason = "weekday_filter";
        candidate.notes = "MNQ_TOP_RUNNER skips Friday entries";
        return candidate;
    }

    return EvaluateLookbackBreakoutCandidate(
        sc,
        bar_index,
        "MNQ_TOP_RUNNER",
        setup_start_time,
        setup_end_time,
        lookback_bars,
        buffer_points,
        delta_threshold,
        close_location_threshold,
        false,
        false,
        0.0,
        stop_points,
        target_points);
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
    if (runner_quantity > 0)
    {
        label_text.Format(
            "AT submitted %s %d+%d\nE %s\nT1 %s  T2 %s\nS %s",
            candidate.direction.c_str(),
            first_leg_quantity,
            runner_quantity,
            FormatNumber(candidate.entry_price).c_str(),
            FormatNumber(candidate.first_target_price).c_str(),
            FormatNumber(candidate.runner_target_price).c_str(),
            FormatNumber(candidate.stop_price).c_str());
    }
    else
    {
        label_text.Format(
            "AT submitted %s %d\nE %s\nT %s\nS %s",
            candidate.direction.c_str(),
            first_leg_quantity,
            FormatNumber(candidate.entry_price).c_str(),
            FormatNumber(candidate.first_target_price).c_str(),
            FormatNumber(candidate.stop_price).c_str());
    }

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
    if (runner_quantity > 0)
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

void DeleteStatusBannerBySlot(SCStudyInterfaceRef sc, int status_slot)
{
    const int drawing_number = kStatusDrawingLineNumberBase + status_slot;
    sc.DeleteACSChartDrawing(sc.ChartNumber, TOOL_DELETE_CHARTDRAWING, drawing_number);
}

void DeleteStatusBanner(SCStudyInterfaceRef sc, bool live_eval_profile)
{
    DeleteStatusBannerBySlot(sc, live_eval_profile ? 1 : 2);
}

void DrawStatusBannerBySlot(
    SCStudyInterfaceRef sc,
    int status_slot,
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
    tool.LineNumber = kStatusDrawingLineNumberBase + status_slot;
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
    DrawStatusBannerBySlot(
        sc,
        live_eval_profile ? 1 : 2,
        latest_closed_bar_index,
        headline,
        gate_line,
        detail_line,
        text_color,
        background_color,
        vertical_position,
        font_size);
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

void RunVwapDeltaExecutionStudy(SCStudyInterfaceRef sc, bool live_eval_profile, bool mnq_eval_profile)
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
    SCInputRef SkipFridayEntries = sc.Input[43];
    SCInputRef SkipElevenHourEntries = sc.Input[44];
    SCInputRef SkipFifteenHourEntries = sc.Input[45];

    const char* live_profile_symbol = mnq_eval_profile ? "MNQ" : "MES";
    const char* live_profile_trade_mode = mnq_eval_profile ? "mnq_eval_live" : "mes_eval_live";
    const char* live_profile_confirmation = mnq_eval_profile
        ? kRequiredMnqEvalConfirmationText
        : kRequiredLiveEvalConfirmationText;

    if (sc.SetDefaults)
    {
        sc.GraphName = live_eval_profile
            ? (mnq_eval_profile ? "AxonTrade MNQ Eval Live Bot" : "AxonTrade MES Eval Live Bot")
            : "AxonTrade VWAP Delta Execution Bot";
        sc.StudyDescription = live_eval_profile
            ? (mnq_eval_profile
                ? "Guarded live-capable MNQ prop-eval execution bot for the AxonTrade local VWAP/delta setup."
                : "Guarded live-capable MES prop-eval execution bot for the AxonTrade VWAP/delta setup.")
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
            ? (mnq_eval_profile
                ? "C:\\SierraChart\\Data\\AxonTrade_MnqEvalLiveBot.csv"
                : "C:\\SierraChart\\Data\\AxonTrade_MesEvalLiveBot.csv")
            : "C:\\SierraChart\\Data\\AxonTrade_VwapDeltaExecutionBot.csv");

        TradeMode.Name = "Trade Mode";
        TradeMode.SetString(live_eval_profile ? live_profile_trade_mode : "execution_sim");

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
        RequiredSymbolPrefix.SetString(live_eval_profile ? live_profile_symbol : "ES");

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
        VwapExtensionPoints.SetFloat(mnq_eval_profile ? 80.0f : 2.0f);

        DeltaThreshold.Name = "Minimum Bar Delta";
        DeltaThreshold.SetFloat(mnq_eval_profile ? 400.0f : 10.0f);

        CloseLocationThreshold.Name = "Close Location Threshold";
        CloseLocationThreshold.SetFloat(mnq_eval_profile ? 0.4f : 0.5f);

        MinimumSpacingSeconds.Name = "Minimum Raw Candidate Spacing Seconds";
        MinimumSpacingSeconds.SetInt(mnq_eval_profile ? 900 : 300);
        MinimumSpacingSeconds.SetIntLimits(0, 7200);

        MaxRawCandidatesPerDay.Name = "Max Raw Candidates Per Day";
        MaxRawCandidatesPerDay.SetInt(20);
        MaxRawCandidatesPerDay.SetIntLimits(0, 200);

        ContextLookbackBars.Name = "Context Lookback Bars";
        ContextLookbackBars.SetInt(mnq_eval_profile ? 1 : 20);
        ContextLookbackBars.SetIntLimits(1, 200);

        MinimumLookbackDirectionalMovePoints.Name = "Maximum Lookback Directional Move Points";
        MinimumLookbackDirectionalMovePoints.SetFloat(mnq_eval_profile ? 999999.0f : -15.0f);

        MinimumSessionRangePoints.Name = "Minimum Session Range Points";
        MinimumSessionRangePoints.SetFloat(mnq_eval_profile ? 0.0f : 30.0f);

        MaxRiskToAverageBarRange.Name = "Max Risk To Average Bar Range";
        MaxRiskToAverageBarRange.SetFloat(mnq_eval_profile ? 999999.0f : 1.7142857f);

        InitialStopPoints.Name = "Initial Stop Points";
        InitialStopPoints.SetFloat(mnq_eval_profile ? 140.0f : 12.0f);

        FirstTargetPoints.Name = "First Target Points";
        FirstTargetPoints.SetFloat(mnq_eval_profile ? 25.0f : 7.0f);

        RunnerTargetPoints.Name = "Runner Target Points";
        RunnerTargetPoints.SetFloat(mnq_eval_profile ? 40.0f : 10.0f);

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
        DailyLossLimitUsd.SetFloat(mnq_eval_profile ? 650.0f : (live_eval_profile ? 240.0f : 2400.0f));

        DailyProfitLockUsd.Name = "Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(live_eval_profile ? 650.0f : 0.0f);

        MoveStopToBreakEvenAfterFirstTarget.Name = "Move Stop To Break Even After First Target";
        MoveStopToBreakEvenAfterFirstTarget.SetYesNo(0);

        BreakEvenOffsetTicks.Name = "Break Even Offset Ticks";
        BreakEvenOffsetTicks.SetInt(0);
        BreakEvenOffsetTicks.SetIntLimits(-20, 20);

        MinimumDirectionalOpenDistancePoints.Name = "Minimum Directional Open Distance Points";
        MinimumDirectionalOpenDistancePoints.SetFloat(mnq_eval_profile ? -999999.0f : -80.0f);

        MaximumSessionRangePoints.Name = "Maximum Session Range Points";
        MaximumSessionRangePoints.SetFloat(mnq_eval_profile ? 0.0f : 100.0f);

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

        SkipFridayEntries.Name = "Skip Friday Entries";
        SkipFridayEntries.SetYesNo(mnq_eval_profile ? 1 : 0);

        SkipElevenHourEntries.Name = "Skip 11:00 Hour Entries";
        SkipElevenHourEntries.SetYesNo(mnq_eval_profile ? 1 : 0);

        SkipFifteenHourEntries.Name = "Skip 15:00 Hour Entries";
        SkipFifteenHourEntries.SetYesNo(mnq_eval_profile ? 1 : 0);

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
        ? live_profile_confirmation
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
            SCString reset_message;
            reset_message.Format(
                "AxonTrade %s eval drawdown tracking reset to current account P/L view.",
                live_profile_symbol);
            sc.AddMessageToLog(reset_message, false);
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
            const std::string live_banner_prefix = std::string("AXON ") + live_profile_symbol + " LIVE";
            if (ArmExecution.GetYesNo() == 0)
            {
                headline = live_banner_prefix + ": STANDBY - NOT ARMED";
                background_color = RGB(96, 72, 0);
            }
            else if (csv_log_path.empty())
            {
                headline = live_banner_prefix + ": BLOCKED - CSV PATH BLANK";
                background_color = RGB(128, 32, 24);
            }
            else if (!route_ok)
            {
                headline = live_banner_prefix + ": BLOCKED - ROUTING OFF";
                background_color = RGB(128, 32, 24);
            }
            else if (!simulation_mode_ok)
            {
                headline = live_banner_prefix + ": BLOCKED - SIERRA SIM MODE IS ON";
                background_color = RGB(128, 32, 24);
            }
            else if (!confirmation_ok)
            {
                headline = live_banner_prefix + ": BLOCKED - CONFIRMATION TEXT";
                background_color = RGB(128, 32, 24);
            }
            else if (allowed_trade_account.empty())
            {
                headline = live_banner_prefix + ": BLOCKED - ALLOWED ACCOUNT BLANK";
                background_color = RGB(128, 32, 24);
            }
            else if (!account_ok)
            {
                headline = live_banner_prefix + ": BLOCKED - ACCOUNT MISMATCH";
                background_color = RGB(128, 32, 24);
            }
            else if (!symbol_ok)
            {
                headline = live_banner_prefix + ": BLOCKED - SYMBOL PREFIX";
                background_color = RGB(128, 32, 24);
            }
            else if (current_chart_downloading_historical_data)
            {
                headline = live_banner_prefix + ": WAIT - HISTORICAL DOWNLOAD";
                background_color = RGB(96, 72, 0);
            }
            else if (daily_lock_active)
            {
                headline = live_banner_prefix + ": LOCKED - DAILY RISK";
                background_color = RGB(128, 32, 24);
            }
            else if (eval_lock_active)
            {
                headline = live_banner_prefix + ": LOCKED - EVAL DRAWDOWN";
                background_color = RGB(128, 32, 24);
            }
            else if (immediate_position_data.PositionQuantity != 0.0 || immediate_position_data.WorkingOrdersExist != 0)
            {
                headline = live_banner_prefix + ": ARMED - MANAGING POSITION/ORDERS";
                background_color = RGB(0, 92, 72);
            }
            else
            {
                headline = live_banner_prefix + ": ARMED - READY FOR LIVE ORDERS";
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
            SkipFridayEntries.GetYesNo() != 0,
            SkipElevenHourEntries.GetYesNo() != 0,
            SkipFifteenHourEntries.GetYesNo() != 0,
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

        const std::string signal_id = SignalId(trade_mode, symbol, bar_index, candidate.direction);
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
                    ? std::string("Confirmation Text must be ") + required_confirmation_text
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
                std::string("Send Orders To Trade Service must be Yes for the ")
                    + live_profile_symbol
                    + " eval live bot");
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
                std::string("Trade >> Trade Simulation Mode On must be off for the ")
                    + live_profile_symbol
                    + " eval live bot");
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

void RunMnqEvalPassCombinedStudy(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef ArmExecution = sc.Input[1];
    SCInputRef SendOrdersToTradeService = sc.Input[2];
    SCInputRef RequireTradeSimulationModeOff = sc.Input[3];
    SCInputRef ConfirmationText = sc.Input[4];
    SCInputRef RequiredSymbolPrefix = sc.Input[5];
    SCInputRef AllowedTradeAccount = sc.Input[6];
    SCInputRef LogRejections = sc.Input[7];
    SCInputRef ProcessFullRecalculation = sc.Input[8];
    SCInputRef ResetCsvOnFullRecalculation = sc.Input[9];
    SCInputRef SetupStartTime = sc.Input[10];
    SCInputRef SetupEndTime = sc.Input[11];
    SCInputRef FlattenTime = sc.Input[12];
    SCInputRef EnableAPlusModule = sc.Input[13];
    SCInputRef EnableBFastModule = sc.Input[14];
    SCInputRef APlusQuantity = sc.Input[15];
    SCInputRef BFastQuantity = sc.Input[16];
    SCInputRef MaxPositionQuantity = sc.Input[17];
    SCInputRef DailyLossLimitUsd = sc.Input[18];
    SCInputRef DailyProfitLockUsd = sc.Input[19];
    SCInputRef MaxEvalTrailingDrawdownUsd = sc.Input[20];
    SCInputRef ResetEvalDrawdownTracking = sc.Input[21];
    SCInputRef DrawStatusBannerInput = sc.Input[22];
    SCInputRef StatusBannerVerticalPosition = sc.Input[23];
    SCInputRef StatusBannerFontSize = sc.Input[24];
    SCInputRef AcceptedSetupAlertSound = sc.Input[25];
    SCInputRef DrawTradeMarkersAndLevels = sc.Input[26];
    SCInputRef TradeLevelForwardBars = sc.Input[27];

    const int status_slot = 3;
    const std::string trade_mode = "mnq_eval_pass_ab_live";

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade MNQ Eval Pass Combined Bot";
        sc.StudyDescription =
            "Guarded live-capable MNQ eval-pass bot for the combined A+ and faster-B wave-rider candidate.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        sc.AllowMultipleEntriesInSameDirection = false;
        sc.MaximumPositionAllowed = 12;
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
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_MnqEvalPassCombinedBot.csv");

        ArmExecution.Name = "Arm Execution";
        ArmExecution.SetYesNo(0);

        SendOrdersToTradeService.Name = "Send Orders To Trade Service";
        SendOrdersToTradeService.SetYesNo(0);

        RequireTradeSimulationModeOff.Name = "Require Trade Simulation Mode Off";
        RequireTradeSimulationModeOff.SetYesNo(1);

        ConfirmationText.Name = "Confirmation Text";
        ConfirmationText.SetString("");

        RequiredSymbolPrefix.Name = "Required Symbol Prefix";
        RequiredSymbolPrefix.SetString("MNQ");

        AllowedTradeAccount.Name = "Allowed Trade Account";
        AllowedTradeAccount.SetString("");

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(0);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        ResetCsvOnFullRecalculation.Name = "Reset CSV On Full Recalculation";
        ResetCsvOnFullRecalculation.SetYesNo(1);

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(10, 0, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(12, 30, 0));

        FlattenTime.Name = "Flatten Time";
        FlattenTime.SetTime(HMS_TIME(16, 40, 0));

        EnableAPlusModule.Name = "Enable A Plus Module";
        EnableAPlusModule.SetYesNo(1);

        EnableBFastModule.Name = "Enable B Fast Module";
        EnableBFastModule.SetYesNo(1);

        APlusQuantity.Name = "A Plus Quantity";
        APlusQuantity.SetInt(12);
        APlusQuantity.SetIntLimits(1, 100);

        BFastQuantity.Name = "B Fast Quantity";
        BFastQuantity.SetInt(4);
        BFastQuantity.SetIntLimits(1, 100);

        MaxPositionQuantity.Name = "Max Position Quantity";
        MaxPositionQuantity.SetInt(12);
        MaxPositionQuantity.SetIntLimits(1, 100);

        DailyLossLimitUsd.Name = "Daily Loss Lock USD";
        DailyLossLimitUsd.SetFloat(900.0f);

        DailyProfitLockUsd.Name = "Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(650.0f);

        MaxEvalTrailingDrawdownUsd.Name = "Max Eval Trailing Drawdown USD";
        MaxEvalTrailingDrawdownUsd.SetFloat(1000.0f);

        ResetEvalDrawdownTracking.Name = "Reset Eval Drawdown Tracking";
        ResetEvalDrawdownTracking.SetYesNo(0);

        DrawStatusBannerInput.Name = "Draw Status Banner";
        DrawStatusBannerInput.SetYesNo(1);

        StatusBannerVerticalPosition.Name = "Status Banner Vertical Position";
        StatusBannerVerticalPosition.SetInt(92);
        StatusBannerVerticalPosition.SetIntLimits(5, 98);

        StatusBannerFontSize.Name = "Status Banner Font Size";
        StatusBannerFontSize.SetInt(10);
        StatusBannerFontSize.SetIntLimits(6, 24);

        AcceptedSetupAlertSound.Name = "Accepted Setup Alert Sound";
        AcceptedSetupAlertSound.SetAlertSoundNumber(1);

        DrawTradeMarkersAndLevels.Name = "Draw Trade Markers And Levels";
        DrawTradeMarkersAndLevels.SetYesNo(1);

        TradeLevelForwardBars.Name = "Trade Level Forward Bars";
        TradeLevelForwardBars.SetInt(36);
        TradeLevelForwardBars.SetIntLimits(1, 500);

        return;
    }

    if (sc.LastCallToFunction)
    {
        DeleteStatusBannerBySlot(sc, status_slot);
        DeleteTrackedBotOrders(sc);
        return;
    }

    sc.SendOrdersToTradeService = SendOrdersToTradeService.GetYesNo() != 0;
    sc.MaximumPositionAllowed = MaxPositionQuantity.GetInt();
    sc.SupportTradingScaleIn = 0;
    sc.SupportTradingScaleOut = 0;

    if (sc.ArraySize <= 1)
        return;

    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    const int latest_closed_bar_index = LatestClosedBarIndex(sc);
    if (latest_closed_bar_index < 0)
        return;

    int& last_processed_bar_index = sc.GetPersistentInt(51);
    int& full_recalculation_reset_done = sc.GetPersistentInt(52);
    int& processing_initialized = sc.GetPersistentInt(53);
    int& last_submitted_trade_date = sc.GetPersistentInt(54);
    int& flatten_date = sc.GetPersistentInt(55);

    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        if (full_recalculation_reset_done == 0)
        {
            last_processed_bar_index = -1;
            last_submitted_trade_date = 0;
            flatten_date = 0;
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
    const std::string required_symbol_prefix = ToStdString(RequiredSymbolPrefix.GetString());
    const std::string allowed_trade_account = ToStdString(AllowedTradeAccount.GetString());
    const bool current_chart_downloading_historical_data =
        sc.DownloadingHistoricalData != 0
        || sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0;

    DrawTrackedOrderFills(
        sc,
        symbol,
        trade_account,
        DrawTradeMarkersAndLevels.GetYesNo() != 0);

    s_SCPositionData immediate_position_data;
    sc.GetTradePosition(immediate_position_data);

    if (ResetEvalDrawdownTracking.GetYesNo() != 0)
    {
        ResetEvalTrailingState(sc, immediate_position_data);
        ResetEvalDrawdownTracking.SetYesNo(0);
        sc.AddMessageToLog("AxonTrade MNQ A+B eval drawdown tracking reset to current account P/L view.", false);
    }
    else
    {
        EnsureEvalTrailingState(sc, immediate_position_data);
    }

    const bool route_ok = SendOrdersToTradeService.GetYesNo() != 0;
    const bool confirmation_ok =
        ToStdString(ConfirmationText.GetString()) == kRequiredMnqEvalPassCombinedConfirmationText;
    const bool symbol_ok = StartsWith(symbol, required_symbol_prefix);
    const bool simulation_mode_ok =
        RequireTradeSimulationModeOff.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0;
    const bool account_ok = !allowed_trade_account.empty() && trade_account == allowed_trade_account;
    const bool live_operational_controls_allowed =
        ArmExecution.GetYesNo() != 0
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

        if (ArmExecution.GetYesNo() == 0)
            headline = "AXON MNQ A+B LIVE: STANDBY - NOT ARMED";
        else if (csv_log_path.empty())
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - CSV PATH BLANK";
            background_color = RGB(128, 32, 24);
        }
        else if (!route_ok)
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - ROUTING OFF";
            background_color = RGB(128, 32, 24);
        }
        else if (!simulation_mode_ok)
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - SIERRA SIM MODE IS ON";
            background_color = RGB(128, 32, 24);
        }
        else if (!confirmation_ok)
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - CONFIRMATION TEXT";
            background_color = RGB(128, 32, 24);
        }
        else if (allowed_trade_account.empty())
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - ALLOWED ACCOUNT BLANK";
            background_color = RGB(128, 32, 24);
        }
        else if (!account_ok)
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - ACCOUNT MISMATCH";
            background_color = RGB(128, 32, 24);
        }
        else if (!symbol_ok)
        {
            headline = "AXON MNQ A+B LIVE: BLOCKED - SYMBOL PREFIX";
            background_color = RGB(128, 32, 24);
        }
        else if (current_chart_downloading_historical_data)
        {
            headline = "AXON MNQ A+B LIVE: WAIT - HISTORICAL DOWNLOAD";
            background_color = RGB(96, 72, 0);
        }
        else if (daily_lock_active)
        {
            headline = "AXON MNQ A+B LIVE: LOCKED - DAILY RISK";
            background_color = RGB(128, 32, 24);
        }
        else if (eval_lock_active)
        {
            headline = "AXON MNQ A+B LIVE: LOCKED - EVAL DRAWDOWN";
            background_color = RGB(128, 32, 24);
        }
        else if (immediate_position_data.PositionQuantity != 0.0 || immediate_position_data.WorkingOrdersExist != 0)
        {
            headline = "AXON MNQ A+B LIVE: ARMED - MANAGING POSITION/ORDERS";
            background_color = RGB(0, 92, 72);
        }
        else
        {
            headline = "AXON MNQ A+B LIVE: ARMED - READY FOR LIVE ORDERS";
            background_color = RGB(0, 96, 32);
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
                  << " A+=" << YesNoStatus(EnableAPlusModule.GetYesNo() != 0)
                  << " B=" << YesNoStatus(EnableBFastModule.GetYesNo() != 0)
                  << " locks=" << (daily_lock_active || eval_lock_active ? "ON" : "OK");

        std::ostringstream detail_line;
        detail_line << "Acct=" << (trade_account.empty() ? "<none>" : trade_account)
                    << " Sym=" << symbol
                    << " Pos=" << FormatNumber(immediate_position_data.PositionQuantity)
                    << " Wkg=" << immediate_position_data.WorkingOrdersExist
                    << " DPL=" << FormatNumber(DailyProfitView(immediate_position_data))
                    << " one/day=" << (last_submitted_trade_date == sc.BaseDateTimeIn[latest_closed_bar_index].GetDate() ? "USED" : "OPEN");

        DrawStatusBannerBySlot(
            sc,
            status_slot,
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
        DeleteStatusBannerBySlot(sc, status_slot);
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
        const bool order_functions_allowed =
            ArmExecution.GetYesNo() != 0
            && SendOrdersToTradeService.GetYesNo() != 0
            && ToStdString(ConfirmationText.GetString()) == kRequiredMnqEvalPassCombinedConfirmationText
            && (RequireTradeSimulationModeOff.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0)
            && !allowed_trade_account.empty()
            && trade_account == allowed_trade_account
            && StartsWith(symbol, required_symbol_prefix)
            && !chart_downloading_historical_data
            && sc.IsFullRecalculation == 0;

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

        SignalCandidate a_plus_candidate;
        SignalCandidate b_fast_candidate;
        if (EnableAPlusModule.GetYesNo() != 0)
        {
            a_plus_candidate = EvaluateLookbackBreakoutCandidate(
                sc,
                bar_index,
                "A_PLUS",
                SetupStartTime.GetTime(),
                SetupEndTime.GetTime(),
                40,
                2.5,
                600.0,
                0.5,
                false,
                false,
                1000.0,
                30.5,
                31.0);
        }
        if (EnableBFastModule.GetYesNo() != 0)
        {
            b_fast_candidate = EvaluateLookbackBreakoutCandidate(
                sc,
                bar_index,
                "B_FAST",
                SetupStartTime.GetTime(),
                SetupEndTime.GetTime(),
                10,
                0.0,
                300.0,
                0.55,
                true,
                true,
                0.0,
                55.5,
                82.0);
        }

        SignalCandidate candidate;
        std::string selected_module;
        int selected_quantity = 0;
        double selected_stop_points = 0.0;
        double selected_target_points = 0.0;
        if (b_fast_candidate.accepted)
        {
            candidate = b_fast_candidate;
            selected_module = "B_FAST";
            selected_quantity = BFastQuantity.GetInt();
            selected_stop_points = 55.5;
            selected_target_points = 82.0;
        }
        else if (a_plus_candidate.accepted)
        {
            candidate = a_plus_candidate;
            selected_module = "A_PLUS";
            selected_quantity = APlusQuantity.GetInt();
            selected_stop_points = 30.5;
            selected_target_points = 31.0;
        }

        if (selected_module.empty())
        {
            if (LogRejections.GetYesNo() != 0)
            {
                candidate.rejection_reason = "no_combined_setup";
                std::ostringstream notes;
                notes << "A_PLUS=" << a_plus_candidate.notes
                      << "; B_FAST=" << b_fast_candidate.notes;
                candidate.notes = notes.str();
                const std::string signal_id = SignalId(trade_mode, symbol, bar_index, candidate.direction);
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

        const std::string signal_id = SignalId(trade_mode, symbol, bar_index, candidate.direction)
            + "_" + selected_module;
        const int first_leg_quantity = selected_quantity;
        const int runner_quantity = 0;

        bool can_submit = true;
        rejection_reason = "not_applicable";
        rejection_notes = "ready";
        if (ArmExecution.GetYesNo() == 0)
        {
            can_submit = false;
            rejection_reason = "execution_not_armed";
            rejection_notes = "Arm Execution is No";
        }
        else if (ToStdString(ConfirmationText.GetString()) != kRequiredMnqEvalPassCombinedConfirmationText)
        {
            can_submit = false;
            rejection_reason = "confirmation_text_missing";
            rejection_notes = std::string("Confirmation Text must be ")
                + kRequiredMnqEvalPassCombinedConfirmationText;
        }
        else if (SendOrdersToTradeService.GetYesNo() == 0)
        {
            can_submit = false;
            rejection_reason = "live_trade_service_not_enabled";
            rejection_notes = "Send Orders To Trade Service must be Yes for the MNQ A+B eval-pass bot";
        }
        else if (RequireTradeSimulationModeOff.GetYesNo() != 0 && sc.GlobalTradeSimulationIsOn != 0)
        {
            can_submit = false;
            rejection_reason = "trade_simulation_mode_must_be_off";
            rejection_notes = "Trade >> Trade Simulation Mode On must be off for the MNQ A+B eval-pass bot";
        }
        else if (allowed_trade_account.empty())
        {
            can_submit = false;
            rejection_reason = "allowed_trade_account_missing";
            rejection_notes = "Allowed Trade Account must exactly match the selected trade account";
        }
        else if (trade_account != allowed_trade_account)
        {
            can_submit = false;
            rejection_reason = "trade_account_gate";
            std::ostringstream notes;
            notes << "selected trade account " << trade_account
                  << " does not match allowed account " << allowed_trade_account;
            rejection_notes = notes.str();
        }
        else if (!StartsWith(symbol, required_symbol_prefix))
        {
            can_submit = false;
            rejection_reason = "symbol_prefix_gate";
            std::ostringstream notes;
            notes << "chart symbol " << symbol << " does not start with required prefix "
                  << required_symbol_prefix;
            rejection_notes = notes.str();
        }
        else if (chart_downloading_historical_data)
        {
            can_submit = false;
            rejection_reason = "historical_download_in_progress";
            rejection_notes = "chart is downloading historical data; entry submission skipped";
        }
        else if (sc.IsFullRecalculation != 0)
        {
            can_submit = false;
            rejection_reason = "full_recalculation_order_block";
            rejection_notes = "live-capable bot does not submit orders during full recalculation";
        }
        else if (selected_quantity <= 0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "selected module quantity must be positive";
        }
        else if (selected_quantity > MaxPositionQuantity.GetInt())
        {
            can_submit = false;
            rejection_reason = "max_position_quantity_gate";
            rejection_notes = "selected module quantity exceeds Max Position Quantity";
        }
        else if (last_submitted_trade_date == current_date)
        {
            can_submit = false;
            rejection_reason = "one_trade_per_day_gate";
            rejection_notes = "combined A+B policy allows exactly one submitted trade per chart date";
        }
        else if (DailyLockBlocksNewEntry(
                sc,
                bar_index,
                position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            can_submit = false;
        }
        else if (EvalTrailingDrawdownBlocks(
                sc,
                position_data,
                MaxEvalTrailingDrawdownUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            can_submit = false;
        }
        else if (position_data.PositionQuantity != 0.0 || position_data.WorkingOrdersExist != 0)
        {
            can_submit = false;
            rejection_reason = "position_or_working_orders_gate";
            rejection_notes = "existing position or working orders are present";
        }

        if (!can_submit)
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
                selected_quantity,
                first_leg_quantity,
                runner_quantity,
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

        AlertAcceptedSetup(
            sc,
            bar_index,
            symbol,
            candidate,
            AcceptedSetupAlertSound.GetAlertSoundNumber());

        s_SCNewOrder new_order;
        new_order.OrderQuantity = selected_quantity;
        new_order.OrderType = SCT_ORDERTYPE_MARKET;
        new_order.TimeInForce = SCT_TIF_GOOD_TILL_CANCELED;
        new_order.TextTag = signal_id.c_str();

        new_order.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
        new_order.Target1Offset = static_cast<float>(selected_target_points);
        new_order.OCOGroup1Quantity = selected_quantity;

        new_order.AttachedOrderStopAllType = SCT_ORDERTYPE_STOP;
        new_order.StopAllOffset = static_cast<float>(selected_stop_points);

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
            last_submitted_trade_date = current_date;
            TrackSubmittedBotOrders(sc, new_order, bar_index, candidate, signal_id);
            if (DrawTradeMarkersAndLevels.GetYesNo() != 0)
            {
                DrawSubmittedTradeOverlay(
                    sc,
                    bar_index,
                    candidate,
                    first_leg_quantity,
                    runner_quantity,
                    MaxInt(1, TradeLevelForwardBars.GetInt()));
            }
            DrawTrackedOrderFills(
                sc,
                symbol,
                trade_account,
                DrawTradeMarkersAndLevels.GetYesNo() != 0);
        }

        std::ostringstream entry_notes;
        entry_notes << candidate.notes
                    << "; selected_module=" << selected_module
                    << "; quantity=" << selected_quantity
                    << "; stop_all_offset_points=" << FormatNumber(selected_stop_points)
                    << "; target1_offset_points=" << FormatNumber(selected_target_points)
                    << "; one_trade_per_day_policy=true";

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
            selected_quantity,
            first_leg_quantity,
            runner_quantity,
            order_result,
            new_order.InternalOrderID,
            new_order.Target1InternalOrderID,
            0,
            new_order.StopAllInternalOrderID,
            after_position_data,
            order_result > 0 ? "not_applicable" : "order_submission_error",
            order_result > 0 ? entry_notes.str() : std::string(sc.GetTradingErrorTextMessage(order_result)));

        last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
    }
}

void RunMgcNormalBreakEvenStudy(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef ArmExecution = sc.Input[1];
    SCInputRef SendOrdersToTradeService = sc.Input[2];
    SCInputRef RequireTradeSimulationModeOffForLive = sc.Input[3];
    SCInputRef RequireTradeSimulationModeOnForSim = sc.Input[4];
    SCInputRef ConfirmationText = sc.Input[5];
    SCInputRef RequiredSymbolPrefix = sc.Input[6];
    SCInputRef AllowedTradeAccount = sc.Input[7];
    SCInputRef LogRejections = sc.Input[8];
    SCInputRef ProcessFullRecalculation = sc.Input[9];
    SCInputRef ResetCsvOnFullRecalculation = sc.Input[10];
    SCInputRef SetupStartTime = sc.Input[11];
    SCInputRef SetupEndTime = sc.Input[12];
    SCInputRef FlattenTime = sc.Input[13];
    SCInputRef Quantity = sc.Input[14];
    SCInputRef MaxPositionQuantity = sc.Input[15];
    SCInputRef DailyLossLimitUsd = sc.Input[16];
    SCInputRef DailyProfitLockUsd = sc.Input[17];
    SCInputRef LookbackBars = sc.Input[18];
    SCInputRef BufferPoints = sc.Input[19];
    SCInputRef DeltaThreshold = sc.Input[20];
    SCInputRef DirectionalCloseLocationThreshold = sc.Input[21];
    SCInputRef MaxAbsDelta = sc.Input[22];
    SCInputRef TargetPoints = sc.Input[23];
    SCInputRef StopPoints = sc.Input[24];
    SCInputRef BreakEvenTriggerPoints = sc.Input[25];
    SCInputRef BreakEvenOffsetTicks = sc.Input[26];
    SCInputRef DrawStatusBannerInput = sc.Input[27];
    SCInputRef StatusBannerVerticalPosition = sc.Input[28];
    SCInputRef StatusBannerFontSize = sc.Input[29];
    SCInputRef AcceptedSetupAlertSound = sc.Input[30];
    SCInputRef DrawTradeMarkersAndLevels = sc.Input[31];
    SCInputRef TradeLevelForwardBars = sc.Input[32];

    const int status_slot = 4;

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade MGC Normal BreakEven Bot";
        sc.StudyDescription =
            "Guarded MGC normal-profitability lookback-breakout bot with 25/15 exits and +20 point break-even.";
        sc.AutoLoop = 0;
        sc.GraphRegion = 0;
        sc.UpdateAlways = 1;

        sc.AllowMultipleEntriesInSameDirection = false;
        sc.MaximumPositionAllowed = 1;
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
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_MgcNormalBreakEvenBot.csv");

        ArmExecution.Name = "Arm Execution";
        ArmExecution.SetYesNo(0);

        SendOrdersToTradeService.Name = "Send Orders To Trade Service";
        SendOrdersToTradeService.SetYesNo(0);

        RequireTradeSimulationModeOffForLive.Name = "Require Trade Simulation Mode Off For Live";
        RequireTradeSimulationModeOffForLive.SetYesNo(1);

        RequireTradeSimulationModeOnForSim.Name = "Require Trade Simulation Mode On For Sim";
        RequireTradeSimulationModeOnForSim.SetYesNo(1);

        ConfirmationText.Name = "Confirmation Text";
        ConfirmationText.SetString("");

        RequiredSymbolPrefix.Name = "Required Symbol Prefix";
        RequiredSymbolPrefix.SetString("MGC");

        AllowedTradeAccount.Name = "Allowed Trade Account";
        AllowedTradeAccount.SetString("");

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(0);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        ResetCsvOnFullRecalculation.Name = "Reset CSV On Full Recalculation";
        ResetCsvOnFullRecalculation.SetYesNo(1);

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(8, 20, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(10, 30, 0));

        FlattenTime.Name = "Flatten Time";
        FlattenTime.SetTime(HMS_TIME(16, 30, 0));

        Quantity.Name = "Quantity";
        Quantity.SetInt(1);
        Quantity.SetIntLimits(1, 100);

        MaxPositionQuantity.Name = "Max Position Quantity";
        MaxPositionQuantity.SetInt(1);
        MaxPositionQuantity.SetIntLimits(1, 100);

        DailyLossLimitUsd.Name = "Daily Loss Lock USD";
        DailyLossLimitUsd.SetFloat(500.0f);

        DailyProfitLockUsd.Name = "Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(0.0f);

        LookbackBars.Name = "Lookback Bars";
        LookbackBars.SetInt(10);
        LookbackBars.SetIntLimits(1, 500);

        BufferPoints.Name = "Buffer Points";
        BufferPoints.SetFloat(0.0f);

        DeltaThreshold.Name = "Delta Threshold";
        DeltaThreshold.SetFloat(0.0f);

        DirectionalCloseLocationThreshold.Name = "Directional Close Location Threshold";
        DirectionalCloseLocationThreshold.SetFloat(0.45f);

        MaxAbsDelta.Name = "Max Absolute Delta";
        MaxAbsDelta.SetFloat(125.0f);

        TargetPoints.Name = "Target Points";
        TargetPoints.SetFloat(25.0f);

        StopPoints.Name = "Stop Points";
        StopPoints.SetFloat(15.0f);

        BreakEvenTriggerPoints.Name = "Break Even Trigger Points";
        BreakEvenTriggerPoints.SetFloat(20.0f);

        BreakEvenOffsetTicks.Name = "Break Even Offset Ticks";
        BreakEvenOffsetTicks.SetInt(0);
        BreakEvenOffsetTicks.SetIntLimits(-20, 20);

        DrawStatusBannerInput.Name = "Draw Status Banner";
        DrawStatusBannerInput.SetYesNo(1);

        StatusBannerVerticalPosition.Name = "Status Banner Vertical Position";
        StatusBannerVerticalPosition.SetInt(88);
        StatusBannerVerticalPosition.SetIntLimits(5, 98);

        StatusBannerFontSize.Name = "Status Banner Font Size";
        StatusBannerFontSize.SetInt(10);
        StatusBannerFontSize.SetIntLimits(6, 24);

        AcceptedSetupAlertSound.Name = "Accepted Setup Alert Sound";
        AcceptedSetupAlertSound.SetAlertSoundNumber(1);

        DrawTradeMarkersAndLevels.Name = "Draw Trade Markers And Levels";
        DrawTradeMarkersAndLevels.SetYesNo(1);

        TradeLevelForwardBars.Name = "Trade Level Forward Bars";
        TradeLevelForwardBars.SetInt(120);
        TradeLevelForwardBars.SetIntLimits(1, 1000);

        return;
    }

    if (sc.LastCallToFunction)
    {
        DeleteStatusBannerBySlot(sc, status_slot);
        DeleteTrackedBotOrders(sc);
        return;
    }

    const bool route_to_trade_service = SendOrdersToTradeService.GetYesNo() != 0;
    const std::string trade_mode = route_to_trade_service ? "mgc_normal_live" : "mgc_normal_sim";
    const char* required_confirmation_text = route_to_trade_service
        ? kRequiredMgcNormalLiveConfirmationText
        : kRequiredMgcNormalSimConfirmationText;

    sc.SendOrdersToTradeService = route_to_trade_service;
    sc.MaximumPositionAllowed = MaxPositionQuantity.GetInt();
    sc.SupportTradingScaleIn = 0;
    sc.SupportTradingScaleOut = 0;

    if (sc.ArraySize <= 1)
        return;

    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    const int latest_closed_bar_index = LatestClosedBarIndex(sc);
    if (latest_closed_bar_index < 0)
        return;

    int& last_processed_bar_index = sc.GetPersistentInt(61);
    int& full_recalculation_reset_done = sc.GetPersistentInt(62);
    int& processing_initialized = sc.GetPersistentInt(63);
    int& last_submitted_trade_date = sc.GetPersistentInt(64);
    int& flatten_date = sc.GetPersistentInt(65);

    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        if (full_recalculation_reset_done == 0)
        {
            last_processed_bar_index = -1;
            last_submitted_trade_date = 0;
            flatten_date = 0;
            processing_initialized = 1;
            if (ResetCsvOnFullRecalculation.GetYesNo() != 0 && !csv_log_path.empty())
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
    const std::string required_symbol_prefix = ToStdString(RequiredSymbolPrefix.GetString());
    const std::string allowed_trade_account = ToStdString(AllowedTradeAccount.GetString());
    const bool current_chart_downloading_historical_data =
        sc.DownloadingHistoricalData != 0
        || sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0;

    DrawTrackedOrderFills(
        sc,
        symbol,
        trade_account,
        DrawTradeMarkersAndLevels.GetYesNo() != 0);

    s_SCPositionData immediate_position_data;
    sc.GetTradePosition(immediate_position_data);

    const bool confirmation_ok = ToStdString(ConfirmationText.GetString()) == required_confirmation_text;
    const bool symbol_ok = StartsWith(symbol, required_symbol_prefix);
    const bool simulation_mode_ok = route_to_trade_service
        ? (RequireTradeSimulationModeOffForLive.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0)
        : (RequireTradeSimulationModeOnForSim.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0);
    const bool account_ok = !route_to_trade_service
        || (!allowed_trade_account.empty() && trade_account == allowed_trade_account);
    const bool operational_controls_allowed =
        ArmExecution.GetYesNo() != 0
        && !csv_log_path.empty()
        && confirmation_ok
        && simulation_mode_ok
        && account_ok
        && symbol_ok
        && !current_chart_downloading_historical_data;

    bool daily_lock_active = false;
    if (operational_controls_allowed)
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
    }

    sc.GetTradePosition(immediate_position_data);

    if (DrawStatusBannerInput.GetYesNo() != 0)
    {
        std::string headline;
        COLORREF text_color = RGB(255, 255, 255);
        COLORREF background_color = RGB(96, 72, 0);
        const std::string mode_label = route_to_trade_service ? "LIVE" : "SIM";

        if (ArmExecution.GetYesNo() == 0)
            headline = "AXON MGC " + mode_label + ": STANDBY - NOT ARMED";
        else if (csv_log_path.empty())
        {
            headline = "AXON MGC " + mode_label + ": BLOCKED - CSV PATH BLANK";
            background_color = RGB(128, 32, 24);
        }
        else if (!confirmation_ok)
        {
            headline = "AXON MGC " + mode_label + ": BLOCKED - CONFIRMATION TEXT";
            background_color = RGB(128, 32, 24);
        }
        else if (!simulation_mode_ok)
        {
            headline = route_to_trade_service
                ? "AXON MGC LIVE: BLOCKED - SIERRA SIM MODE IS ON"
                : "AXON MGC SIM: BLOCKED - SIERRA SIM MODE IS OFF";
            background_color = RGB(128, 32, 24);
        }
        else if (route_to_trade_service && allowed_trade_account.empty())
        {
            headline = "AXON MGC LIVE: BLOCKED - ALLOWED ACCOUNT BLANK";
            background_color = RGB(128, 32, 24);
        }
        else if (!account_ok)
        {
            headline = "AXON MGC LIVE: BLOCKED - ACCOUNT MISMATCH";
            background_color = RGB(128, 32, 24);
        }
        else if (!symbol_ok)
        {
            headline = "AXON MGC " + mode_label + ": BLOCKED - SYMBOL PREFIX";
            background_color = RGB(128, 32, 24);
        }
        else if (current_chart_downloading_historical_data)
        {
            headline = "AXON MGC " + mode_label + ": WAIT - HISTORICAL DOWNLOAD";
            background_color = RGB(96, 72, 0);
        }
        else if (daily_lock_active)
        {
            headline = "AXON MGC " + mode_label + ": LOCKED - DAILY RISK";
            background_color = RGB(128, 32, 24);
        }
        else if (immediate_position_data.PositionQuantity != 0.0 || immediate_position_data.WorkingOrdersExist != 0)
        {
            headline = "AXON MGC " + mode_label + ": ARMED - MANAGING POSITION/ORDERS";
            background_color = RGB(0, 92, 72);
        }
        else
        {
            headline = "AXON MGC " + mode_label + ": ARMED - READY";
            background_color = RGB(0, 96, 32);
        }

        std::ostringstream gate_line;
        gate_line << "Gates: arm=" << YesNoStatus(ArmExecution.GetYesNo() != 0)
                  << " route=" << (route_to_trade_service ? "LIVE" : "SIM")
                  << " sim=" << (sc.GlobalTradeSimulationIsOn != 0 ? "ON" : "OFF")
                  << " simGate=" << YesNoStatus(simulation_mode_ok)
                  << " confirm=" << YesNoStatus(confirmation_ok)
                  << " acct=" << YesNoStatus(account_ok)
                  << " symbol=" << YesNoStatus(symbol_ok)
                  << " data=" << (current_chart_downloading_historical_data ? "DL" : "OK")
                  << " locks=" << (daily_lock_active ? "ON" : "OK");

        std::ostringstream detail_line;
        detail_line << "Acct=" << (trade_account.empty() ? "<none>" : trade_account)
                    << " Sym=" << symbol
                    << " Pos=" << FormatNumber(immediate_position_data.PositionQuantity)
                    << " Wkg=" << immediate_position_data.WorkingOrdersExist
                    << " DPL=" << FormatNumber(DailyProfitView(immediate_position_data))
                    << " one/day=" << (last_submitted_trade_date == sc.BaseDateTimeIn[latest_closed_bar_index].GetDate() ? "USED" : "OPEN")
                    << " q=" << Quantity.GetInt();

        DrawStatusBannerBySlot(
            sc,
            status_slot,
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
        DeleteStatusBannerBySlot(sc, status_slot);
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
        const bool current_route_to_trade_service = SendOrdersToTradeService.GetYesNo() != 0;
        const std::string current_trade_mode = current_route_to_trade_service ? "mgc_normal_live" : "mgc_normal_sim";
        const char* current_required_confirmation_text = current_route_to_trade_service
            ? kRequiredMgcNormalLiveConfirmationText
            : kRequiredMgcNormalSimConfirmationText;
        const bool current_simulation_mode_ok = current_route_to_trade_service
            ? (RequireTradeSimulationModeOffForLive.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn == 0)
            : (RequireTradeSimulationModeOnForSim.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0);
        const bool current_account_ok = !current_route_to_trade_service
            || (!allowed_trade_account.empty() && trade_account == allowed_trade_account);
        const bool order_functions_allowed =
            ArmExecution.GetYesNo() != 0
            && ToStdString(ConfirmationText.GetString()) == current_required_confirmation_text
            && current_simulation_mode_ok
            && current_account_ok
            && StartsWith(symbol, required_symbol_prefix)
            && !chart_downloading_historical_data
            && sc.IsFullRecalculation == 0;

        if (order_functions_allowed && bar_time >= FlattenTime.GetTime() && flatten_date != current_date)
        {
            FlattenIfNeeded(
                sc,
                csv_log_path,
                symbol,
                trade_account,
                current_trade_mode,
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
                    current_trade_mode,
                    bar_index,
                    "daily_lock_flatten",
                    rejection_notes);
                sc.GetTradePosition(position_data);
            }
        }

        SignalCandidate candidate = EvaluateMgcNormalBreakEvenCandidate(
            sc,
            bar_index,
            SetupStartTime.GetTime(),
            SetupEndTime.GetTime(),
            LookbackBars.GetInt(),
            BufferPoints.GetFloat(),
            DeltaThreshold.GetFloat(),
            DirectionalCloseLocationThreshold.GetFloat(),
            MaxAbsDelta.GetFloat(),
            StopPoints.GetFloat(),
            TargetPoints.GetFloat());

        const std::string signal_id = SignalId(current_trade_mode, symbol, bar_index, candidate.direction);
        if (!candidate.accepted)
        {
            if (LogRejections.GetYesNo() != 0)
            {
                LogCandidateEvent(
                    sc,
                    csv_log_path,
                    "execution_signal_rejected",
                    symbol,
                    trade_account,
                    current_trade_mode,
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

        const int selected_quantity = Quantity.GetInt();
        const int first_leg_quantity = selected_quantity;
        const int runner_quantity = 0;

        bool can_submit = true;
        rejection_reason = "not_applicable";
        rejection_notes = "ready";
        if (ArmExecution.GetYesNo() == 0)
        {
            can_submit = false;
            rejection_reason = "execution_not_armed";
            rejection_notes = "Arm Execution is No";
        }
        else if (ToStdString(ConfirmationText.GetString()) != current_required_confirmation_text)
        {
            can_submit = false;
            rejection_reason = "confirmation_text_missing";
            rejection_notes = std::string("Confirmation Text must be ") + current_required_confirmation_text;
        }
        else if (!current_simulation_mode_ok)
        {
            can_submit = false;
            rejection_reason = current_route_to_trade_service
                ? "trade_simulation_mode_must_be_off"
                : "trade_simulation_mode_must_be_on";
            rejection_notes = current_route_to_trade_service
                ? "Trade >> Trade Simulation Mode On must be off for live MGC routing"
                : "Trade >> Trade Simulation Mode On must be on for MGC sim/replay mode";
        }
        else if (current_route_to_trade_service && allowed_trade_account.empty())
        {
            can_submit = false;
            rejection_reason = "allowed_trade_account_missing";
            rejection_notes = "Allowed Trade Account must exactly match the selected trade account for live routing";
        }
        else if (!current_account_ok)
        {
            can_submit = false;
            rejection_reason = "trade_account_gate";
            std::ostringstream notes;
            notes << "selected trade account " << trade_account
                  << " does not match allowed account " << allowed_trade_account;
            rejection_notes = notes.str();
        }
        else if (!StartsWith(symbol, required_symbol_prefix))
        {
            can_submit = false;
            rejection_reason = "symbol_prefix_gate";
            std::ostringstream notes;
            notes << "chart symbol " << symbol << " does not start with required prefix "
                  << required_symbol_prefix;
            rejection_notes = notes.str();
        }
        else if (chart_downloading_historical_data)
        {
            can_submit = false;
            rejection_reason = "historical_download_in_progress";
            rejection_notes = "chart is downloading historical data; entry submission skipped";
        }
        else if (sc.IsFullRecalculation != 0)
        {
            can_submit = false;
            rejection_reason = "full_recalculation_order_block";
            rejection_notes = "MGC bot does not submit orders during full recalculation";
        }
        else if (selected_quantity <= 0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "Quantity must be positive";
        }
        else if (selected_quantity > MaxPositionQuantity.GetInt())
        {
            can_submit = false;
            rejection_reason = "max_position_quantity_gate";
            rejection_notes = "Quantity exceeds Max Position Quantity";
        }
        else if (TargetPoints.GetFloat() <= 0.0 || StopPoints.GetFloat() <= 0.0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "Target Points and Stop Points must be positive";
        }
        else if (BreakEvenTriggerPoints.GetFloat() <= 0.0 || sc.TickSize <= 0.0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "Break Even Trigger Points and chart Tick Size must be positive";
        }
        else if (last_submitted_trade_date == current_date)
        {
            can_submit = false;
            rejection_reason = "one_trade_per_day_gate";
            rejection_notes = "MGC normal lead allows exactly one submitted trade per chart date";
        }
        else if (DailyLockBlocksNewEntry(
                sc,
                bar_index,
                position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            can_submit = false;
        }
        else if (position_data.PositionQuantity != 0.0 || position_data.WorkingOrdersExist != 0)
        {
            can_submit = false;
            rejection_reason = "position_or_working_orders_gate";
            rejection_notes = "existing position or working orders are present";
        }

        if (!can_submit)
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
                current_trade_mode,
                bar_index,
                candidate,
                signal_id,
                selected_quantity,
                first_leg_quantity,
                runner_quantity,
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

        AlertAcceptedSetup(
            sc,
            bar_index,
            symbol,
            candidate,
            AcceptedSetupAlertSound.GetAlertSoundNumber());

        s_SCNewOrder new_order;
        new_order.OrderQuantity = selected_quantity;
        new_order.OrderType = SCT_ORDERTYPE_MARKET;
        new_order.TimeInForce = SCT_TIF_GOOD_TILL_CANCELED;
        new_order.TextTag = signal_id.c_str();

        new_order.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
        new_order.Target1Offset = TargetPoints.GetFloat();
        new_order.OCOGroup1Quantity = selected_quantity;

        new_order.AttachedOrderStopAllType = SCT_ORDERTYPE_STOP;
        new_order.StopAllOffset = StopPoints.GetFloat();
        new_order.MoveToBreakEven.Type = MOVETO_BE_ACTION_TYPE_OFFSET_TRIGGERED;
        new_order.MoveToBreakEven.TriggerOffsetInTicks = static_cast<int>(
            std::ceil((BreakEvenTriggerPoints.GetFloat() / sc.TickSize) - 1e-12));
        new_order.MoveToBreakEven.BreakEvenLevelOffsetInTicks = BreakEvenOffsetTicks.GetInt();

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
            last_submitted_trade_date = current_date;
            TrackSubmittedBotOrders(sc, new_order, bar_index, candidate, signal_id);
            if (DrawTradeMarkersAndLevels.GetYesNo() != 0)
            {
                DrawSubmittedTradeOverlay(
                    sc,
                    bar_index,
                    candidate,
                    first_leg_quantity,
                    runner_quantity,
                    MaxInt(1, TradeLevelForwardBars.GetInt()));
            }
            DrawTrackedOrderFills(
                sc,
                symbol,
                trade_account,
                DrawTradeMarkersAndLevels.GetYesNo() != 0);
        }

        std::ostringstream entry_notes;
        entry_notes << candidate.notes
                    << "; quantity=" << selected_quantity
                    << "; stop_all_offset_points=" << FormatNumber(StopPoints.GetFloat())
                    << "; target1_offset_points=" << FormatNumber(TargetPoints.GetFloat())
                    << "; break_even_trigger_points=" << FormatNumber(BreakEvenTriggerPoints.GetFloat())
                    << "; break_even_trigger_ticks=" << new_order.MoveToBreakEven.TriggerOffsetInTicks
                    << "; break_even_offset_ticks=" << BreakEvenOffsetTicks.GetInt()
                    << "; one_trade_per_day_policy=true"
                    << "; route_to_trade_service=" << FormatBool(current_route_to_trade_service);

        LogCandidateEvent(
            sc,
            csv_log_path,
            order_result > 0 ? "execution_entry_submitted" : "execution_entry_error",
            symbol,
            trade_account,
            current_trade_mode,
            bar_index,
            candidate,
            signal_id,
            selected_quantity,
            first_leg_quantity,
            runner_quantity,
            order_result,
            new_order.InternalOrderID,
            new_order.Target1InternalOrderID,
            0,
            new_order.StopAllInternalOrderID,
            after_position_data,
            order_result > 0 ? "not_applicable" : "order_submission_error",
            order_result > 0 ? entry_notes.str() : std::string(sc.GetTradingErrorTextMessage(order_result)));

        last_processed_bar_index = MaxInt(last_processed_bar_index, bar_index);
    }
}

void RunMnqTopRunnerSimStudy(SCStudyInterfaceRef sc)
{
    SCInputRef CsvLogPath = sc.Input[0];
    SCInputRef ArmExecution = sc.Input[1];
    SCInputRef SendOrdersToTradeService = sc.Input[2];
    SCInputRef RequireTradeSimulationModeOnForSim = sc.Input[3];
    SCInputRef ConfirmationText = sc.Input[4];
    SCInputRef RequiredSymbolPrefix = sc.Input[5];
    SCInputRef LogRejections = sc.Input[6];
    SCInputRef ProcessFullRecalculation = sc.Input[7];
    SCInputRef ResetCsvOnFullRecalculation = sc.Input[8];
    SCInputRef SetupStartTime = sc.Input[9];
    SCInputRef SetupEndTime = sc.Input[10];
    SCInputRef FlattenTime = sc.Input[11];
    SCInputRef Quantity = sc.Input[12];
    SCInputRef MaxPositionQuantity = sc.Input[13];
    SCInputRef DailyLossLimitUsd = sc.Input[14];
    SCInputRef DailyProfitLockUsd = sc.Input[15];
    SCInputRef LookbackBars = sc.Input[16];
    SCInputRef BufferPoints = sc.Input[17];
    SCInputRef DeltaThreshold = sc.Input[18];
    SCInputRef DirectionalCloseLocationThreshold = sc.Input[19];
    SCInputRef TargetPoints = sc.Input[20];
    SCInputRef StopPoints = sc.Input[21];
    SCInputRef MinimumSignalSpacingSeconds = sc.Input[22];
    SCInputRef DrawStatusBannerInput = sc.Input[23];
    SCInputRef StatusBannerVerticalPosition = sc.Input[24];
    SCInputRef StatusBannerFontSize = sc.Input[25];
    SCInputRef AcceptedSetupAlertSound = sc.Input[26];
    SCInputRef DrawTradeMarkersAndLevels = sc.Input[27];
    SCInputRef TradeLevelForwardBars = sc.Input[28];

    const int status_slot = 5;

    if (sc.SetDefaults)
    {
        sc.GraphName = "AxonTrade MNQ Top Runner Sim Bot";
        sc.StudyDescription =
            "Simulation-only MNQ normal-profitability lookback-breakout runner candidate.";
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
        CsvLogPath.SetString("C:\\SierraChart\\Data\\AxonTrade_MnqTopRunnerSimBot.csv");

        ArmExecution.Name = "Arm Execution";
        ArmExecution.SetYesNo(0);

        SendOrdersToTradeService.Name = "Send Orders To Trade Service";
        SendOrdersToTradeService.SetYesNo(0);

        RequireTradeSimulationModeOnForSim.Name = "Require Trade Simulation Mode On For Sim";
        RequireTradeSimulationModeOnForSim.SetYesNo(1);

        ConfirmationText.Name = "Confirmation Text";
        ConfirmationText.SetString("");

        RequiredSymbolPrefix.Name = "Required Symbol Prefix";
        RequiredSymbolPrefix.SetString("MNQ");

        LogRejections.Name = "Log Rejections";
        LogRejections.SetYesNo(0);

        ProcessFullRecalculation.Name = "Process Full Recalculation";
        ProcessFullRecalculation.SetYesNo(0);

        ResetCsvOnFullRecalculation.Name = "Reset CSV On Full Recalculation";
        ResetCsvOnFullRecalculation.SetYesNo(1);

        SetupStartTime.Name = "Setup Start Time";
        SetupStartTime.SetTime(HMS_TIME(10, 0, 0));

        SetupEndTime.Name = "Setup End Time";
        SetupEndTime.SetTime(HMS_TIME(11, 0, 0));

        FlattenTime.Name = "Flatten Time";
        FlattenTime.SetTime(HMS_TIME(15, 45, 0));

        Quantity.Name = "Quantity";
        Quantity.SetInt(2);
        Quantity.SetIntLimits(1, 100);

        MaxPositionQuantity.Name = "Max Position Quantity";
        MaxPositionQuantity.SetInt(2);
        MaxPositionQuantity.SetIntLimits(1, 100);

        DailyLossLimitUsd.Name = "Daily Loss Lock USD";
        DailyLossLimitUsd.SetFloat(0.0f);

        DailyProfitLockUsd.Name = "Daily Profit Lock USD";
        DailyProfitLockUsd.SetFloat(0.0f);

        LookbackBars.Name = "Lookback Bars";
        LookbackBars.SetInt(20);
        LookbackBars.SetIntLimits(1, 500);

        BufferPoints.Name = "Buffer Points";
        BufferPoints.SetFloat(0.0f);

        DeltaThreshold.Name = "Delta Threshold";
        DeltaThreshold.SetFloat(600.0f);

        DirectionalCloseLocationThreshold.Name = "Directional Close Location Threshold";
        DirectionalCloseLocationThreshold.SetFloat(0.9f);

        TargetPoints.Name = "Target Points";
        TargetPoints.SetFloat(160.0f);

        StopPoints.Name = "Stop Points";
        StopPoints.SetFloat(70.0f);

        MinimumSignalSpacingSeconds.Name = "Minimum Signal Spacing Seconds";
        MinimumSignalSpacingSeconds.SetInt(3600);
        MinimumSignalSpacingSeconds.SetIntLimits(0, 86400);

        DrawStatusBannerInput.Name = "Draw Status Banner";
        DrawStatusBannerInput.SetYesNo(1);

        StatusBannerVerticalPosition.Name = "Status Banner Vertical Position";
        StatusBannerVerticalPosition.SetInt(82);
        StatusBannerVerticalPosition.SetIntLimits(5, 98);

        StatusBannerFontSize.Name = "Status Banner Font Size";
        StatusBannerFontSize.SetInt(10);
        StatusBannerFontSize.SetIntLimits(6, 24);

        AcceptedSetupAlertSound.Name = "Accepted Setup Alert Sound";
        AcceptedSetupAlertSound.SetAlertSoundNumber(1);

        DrawTradeMarkersAndLevels.Name = "Draw Trade Markers And Levels";
        DrawTradeMarkersAndLevels.SetYesNo(1);

        TradeLevelForwardBars.Name = "Trade Level Forward Bars";
        TradeLevelForwardBars.SetInt(180);
        TradeLevelForwardBars.SetIntLimits(1, 1000);

        return;
    }

    if (sc.LastCallToFunction)
    {
        DeleteStatusBannerBySlot(sc, status_slot);
        DeleteTrackedBotOrders(sc);
        return;
    }

    const bool requested_live_routing = SendOrdersToTradeService.GetYesNo() != 0;
    const std::string trade_mode = "mnq_top_runner_sim";

    sc.SendOrdersToTradeService = false;
    sc.MaximumPositionAllowed = MaxPositionQuantity.GetInt();
    sc.SupportTradingScaleIn = 0;
    sc.SupportTradingScaleOut = 0;

    if (sc.ArraySize <= 1)
        return;

    const std::string csv_log_path = ToStdString(CsvLogPath.GetString());
    const int latest_closed_bar_index = LatestClosedBarIndex(sc);
    if (latest_closed_bar_index < 0)
        return;

    int& last_processed_bar_index = sc.GetPersistentInt(81);
    int& full_recalculation_reset_done = sc.GetPersistentInt(82);
    int& processing_initialized = sc.GetPersistentInt(83);
    int& last_submitted_signal_date = sc.GetPersistentInt(84);
    int& last_submitted_signal_time = sc.GetPersistentInt(85);
    int& flatten_date = sc.GetPersistentInt(86);

    if (sc.IsFullRecalculation && ProcessFullRecalculation.GetYesNo() != 0)
    {
        if (full_recalculation_reset_done == 0)
        {
            last_processed_bar_index = -1;
            last_submitted_signal_date = 0;
            last_submitted_signal_time = -1;
            flatten_date = 0;
            processing_initialized = 1;
            if (ResetCsvOnFullRecalculation.GetYesNo() != 0 && !csv_log_path.empty())
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
            last_submitted_signal_time = -1;
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
    const std::string required_symbol_prefix = ToStdString(RequiredSymbolPrefix.GetString());
    const bool current_chart_downloading_historical_data =
        sc.DownloadingHistoricalData != 0
        || sc.ChartIsDownloadingHistoricalData(sc.ChartNumber) != 0;

    DrawTrackedOrderFills(
        sc,
        symbol,
        trade_account,
        DrawTradeMarkersAndLevels.GetYesNo() != 0);

    s_SCPositionData immediate_position_data;
    sc.GetTradePosition(immediate_position_data);

    const bool confirmation_ok =
        ToStdString(ConfirmationText.GetString()) == kRequiredMnqTopRunnerSimConfirmationText;
    const bool symbol_ok = StartsWith(symbol, required_symbol_prefix);
    const bool simulation_mode_ok =
        RequireTradeSimulationModeOnForSim.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0;
    const bool operational_controls_allowed =
        ArmExecution.GetYesNo() != 0
        && !csv_log_path.empty()
        && confirmation_ok
        && !requested_live_routing
        && simulation_mode_ok
        && symbol_ok
        && !current_chart_downloading_historical_data;

    bool daily_lock_active = false;
    if (operational_controls_allowed)
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
    }

    sc.GetTradePosition(immediate_position_data);

    if (DrawStatusBannerInput.GetYesNo() != 0)
    {
        std::string headline;
        COLORREF text_color = RGB(255, 255, 255);
        COLORREF background_color = RGB(96, 72, 0);

        if (ArmExecution.GetYesNo() == 0)
            headline = "AXON MNQ TOP RUNNER SIM: STANDBY - NOT ARMED";
        else if (csv_log_path.empty())
        {
            headline = "AXON MNQ TOP RUNNER SIM: BLOCKED - CSV PATH BLANK";
            background_color = RGB(128, 32, 24);
        }
        else if (requested_live_routing)
        {
            headline = "AXON MNQ TOP RUNNER SIM: BLOCKED - LIVE ROUTING REJECTED";
            background_color = RGB(128, 32, 24);
        }
        else if (!confirmation_ok)
        {
            headline = "AXON MNQ TOP RUNNER SIM: BLOCKED - CONFIRMATION TEXT";
            background_color = RGB(128, 32, 24);
        }
        else if (!simulation_mode_ok)
        {
            headline = "AXON MNQ TOP RUNNER SIM: BLOCKED - SIERRA SIM MODE IS OFF";
            background_color = RGB(128, 32, 24);
        }
        else if (!symbol_ok)
        {
            headline = "AXON MNQ TOP RUNNER SIM: BLOCKED - SYMBOL PREFIX";
            background_color = RGB(128, 32, 24);
        }
        else if (current_chart_downloading_historical_data)
        {
            headline = "AXON MNQ TOP RUNNER SIM: WAIT - HISTORICAL DOWNLOAD";
            background_color = RGB(96, 72, 0);
        }
        else if (daily_lock_active)
        {
            headline = "AXON MNQ TOP RUNNER SIM: LOCKED - DAILY RISK";
            background_color = RGB(128, 32, 24);
        }
        else if (immediate_position_data.PositionQuantity != 0.0 || immediate_position_data.WorkingOrdersExist != 0)
        {
            headline = "AXON MNQ TOP RUNNER SIM: ARMED - MANAGING POSITION/ORDERS";
            background_color = RGB(0, 92, 72);
        }
        else
        {
            headline = "AXON MNQ TOP RUNNER SIM: ARMED - READY";
            background_color = RGB(0, 96, 32);
        }

        std::ostringstream gate_line;
        gate_line << "Gates: arm=" << YesNoStatus(ArmExecution.GetYesNo() != 0)
                  << " route=" << (requested_live_routing ? "REJECT" : "SIM")
                  << " sim=" << (sc.GlobalTradeSimulationIsOn != 0 ? "ON" : "OFF")
                  << " simGate=" << YesNoStatus(simulation_mode_ok)
                  << " confirm=" << YesNoStatus(confirmation_ok)
                  << " symbol=" << YesNoStatus(symbol_ok)
                  << " data=" << (current_chart_downloading_historical_data ? "DL" : "OK")
                  << " locks=" << (daily_lock_active ? "ON" : "OK");

        const int latest_date = sc.BaseDateTimeIn[latest_closed_bar_index].GetDate();
        std::ostringstream detail_line;
        detail_line << "Acct=" << (trade_account.empty() ? "<none>" : trade_account)
                    << " Sym=" << symbol
                    << " Pos=" << FormatNumber(immediate_position_data.PositionQuantity)
                    << " Wkg=" << immediate_position_data.WorkingOrdersExist
                    << " q=" << Quantity.GetInt()
                    << " target/stop=" << FormatNumber(TargetPoints.GetFloat())
                    << "/" << FormatNumber(StopPoints.GetFloat())
                    << " spacing=" << MinimumSignalSpacingSeconds.GetInt()
                    << " last="
                    << (last_submitted_signal_date == latest_date ? FormatNumber(last_submitted_signal_time) : "none");

        DrawStatusBannerBySlot(
            sc,
            status_slot,
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
        DeleteStatusBannerBySlot(sc, status_slot);
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
        const bool current_requested_live_routing = SendOrdersToTradeService.GetYesNo() != 0;
        const bool current_confirmation_ok =
            ToStdString(ConfirmationText.GetString()) == kRequiredMnqTopRunnerSimConfirmationText;
        const bool current_simulation_mode_ok =
            RequireTradeSimulationModeOnForSim.GetYesNo() == 0 || sc.GlobalTradeSimulationIsOn != 0;
        const bool order_functions_allowed =
            ArmExecution.GetYesNo() != 0
            && current_confirmation_ok
            && !current_requested_live_routing
            && current_simulation_mode_ok
            && StartsWith(symbol, required_symbol_prefix)
            && !chart_downloading_historical_data
            && sc.IsFullRecalculation == 0;

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

        SignalCandidate candidate = EvaluateMnqTopRunnerCandidate(
            sc,
            bar_index,
            SetupStartTime.GetTime(),
            SetupEndTime.GetTime(),
            LookbackBars.GetInt(),
            BufferPoints.GetFloat(),
            DeltaThreshold.GetFloat(),
            DirectionalCloseLocationThreshold.GetFloat(),
            StopPoints.GetFloat(),
            TargetPoints.GetFloat());

        const std::string signal_id = SignalId(trade_mode, symbol, bar_index, candidate.direction);
        if (!candidate.accepted)
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

        const int selected_quantity = Quantity.GetInt();
        const int first_leg_quantity = selected_quantity;
        const int runner_quantity = 0;

        bool spacing_ok = true;
        if (
            MinimumSignalSpacingSeconds.GetInt() > 0
            && last_submitted_signal_date == current_date
            && last_submitted_signal_time >= 0)
        {
            const int seconds_since_last_signal = bar_time - last_submitted_signal_time;
            spacing_ok =
                seconds_since_last_signal < 0
                || seconds_since_last_signal >= MinimumSignalSpacingSeconds.GetInt();
        }

        bool can_submit = true;
        rejection_reason = "not_applicable";
        rejection_notes = "ready";
        if (ArmExecution.GetYesNo() == 0)
        {
            can_submit = false;
            rejection_reason = "execution_not_armed";
            rejection_notes = "Arm Execution is No";
        }
        else if (current_requested_live_routing)
        {
            can_submit = false;
            rejection_reason = "live_routing_rejected";
            rejection_notes = "MNQ top-runner study is simulation/replay only";
        }
        else if (!current_confirmation_ok)
        {
            can_submit = false;
            rejection_reason = "confirmation_text_missing";
            rejection_notes = std::string("Confirmation Text must be ")
                + kRequiredMnqTopRunnerSimConfirmationText;
        }
        else if (!current_simulation_mode_ok)
        {
            can_submit = false;
            rejection_reason = "trade_simulation_mode_must_be_on";
            rejection_notes = "Trade >> Trade Simulation Mode On must be on for MNQ top-runner sim/replay mode";
        }
        else if (!StartsWith(symbol, required_symbol_prefix))
        {
            can_submit = false;
            rejection_reason = "symbol_prefix_gate";
            std::ostringstream notes;
            notes << "chart symbol " << symbol << " does not start with required prefix "
                  << required_symbol_prefix;
            rejection_notes = notes.str();
        }
        else if (chart_downloading_historical_data)
        {
            can_submit = false;
            rejection_reason = "historical_download_in_progress";
            rejection_notes = "chart is downloading historical data; entry submission skipped";
        }
        else if (sc.IsFullRecalculation != 0)
        {
            can_submit = false;
            rejection_reason = "full_recalculation_order_block";
            rejection_notes = "MNQ top-runner bot does not submit orders during full recalculation";
        }
        else if (selected_quantity <= 0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "Quantity must be positive";
        }
        else if (selected_quantity > MaxPositionQuantity.GetInt())
        {
            can_submit = false;
            rejection_reason = "max_position_quantity_gate";
            rejection_notes = "Quantity exceeds Max Position Quantity";
        }
        else if (TargetPoints.GetFloat() <= 0.0 || StopPoints.GetFloat() <= 0.0)
        {
            can_submit = false;
            rejection_reason = "configuration_error";
            rejection_notes = "Target Points and Stop Points must be positive";
        }
        else if (!spacing_ok)
        {
            can_submit = false;
            rejection_reason = "signal_spacing_gate";
            rejection_notes = "minimum signal spacing has not elapsed since the last submitted signal";
        }
        else if (DailyLockBlocksNewEntry(
                sc,
                bar_index,
                position_data,
                DailyLossLimitUsd.GetFloat(),
                DailyProfitLockUsd.GetFloat(),
                rejection_reason,
                rejection_notes))
        {
            can_submit = false;
        }
        else if (position_data.PositionQuantity != 0.0 || position_data.WorkingOrdersExist != 0)
        {
            can_submit = false;
            rejection_reason = "position_or_working_orders_gate";
            rejection_notes = "existing position or working orders are present";
        }

        if (!can_submit)
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
                selected_quantity,
                first_leg_quantity,
                runner_quantity,
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

        AlertAcceptedSetup(
            sc,
            bar_index,
            symbol,
            candidate,
            AcceptedSetupAlertSound.GetAlertSoundNumber());

        s_SCNewOrder new_order;
        new_order.OrderQuantity = selected_quantity;
        new_order.OrderType = SCT_ORDERTYPE_MARKET;
        new_order.TimeInForce = SCT_TIF_GOOD_TILL_CANCELED;
        new_order.TextTag = signal_id.c_str();

        new_order.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
        new_order.Target1Offset = TargetPoints.GetFloat();
        new_order.OCOGroup1Quantity = selected_quantity;

        new_order.AttachedOrderStopAllType = SCT_ORDERTYPE_STOP;
        new_order.StopAllOffset = StopPoints.GetFloat();

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
            last_submitted_signal_date = current_date;
            last_submitted_signal_time = bar_time;
            TrackSubmittedBotOrders(sc, new_order, bar_index, candidate, signal_id);
            if (DrawTradeMarkersAndLevels.GetYesNo() != 0)
            {
                DrawSubmittedTradeOverlay(
                    sc,
                    bar_index,
                    candidate,
                    first_leg_quantity,
                    runner_quantity,
                    MaxInt(1, TradeLevelForwardBars.GetInt()));
            }
            DrawTrackedOrderFills(
                sc,
                symbol,
                trade_account,
                DrawTradeMarkersAndLevels.GetYesNo() != 0);
        }

        std::ostringstream entry_notes;
        entry_notes << candidate.notes
                    << "; quantity=" << selected_quantity
                    << "; stop_all_offset_points=" << FormatNumber(StopPoints.GetFloat())
                    << "; target1_offset_points=" << FormatNumber(TargetPoints.GetFloat())
                    << "; minimum_signal_spacing_seconds=" << MinimumSignalSpacingSeconds.GetInt()
                    << "; simulation_only=true"
                    << "; live_routing_requested=" << FormatBool(current_requested_live_routing);

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
            selected_quantity,
            first_leg_quantity,
            runner_quantity,
            order_result,
            new_order.InternalOrderID,
            new_order.Target1InternalOrderID,
            0,
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
    RunVwapDeltaExecutionStudy(sc, false, false);
}

SCSFExport scsf_AxonTradeVwapDeltaMesEvalLiveBot(SCStudyInterfaceRef sc)
{
    RunVwapDeltaExecutionStudy(sc, true, false);
}

SCSFExport scsf_AxonTradeVwapDeltaMnqEvalLiveBot(SCStudyInterfaceRef sc)
{
    RunVwapDeltaExecutionStudy(sc, true, true);
}

SCSFExport scsf_AxonTradeMnqEvalPassCombinedBot(SCStudyInterfaceRef sc)
{
    RunMnqEvalPassCombinedStudy(sc);
}

SCSFExport scsf_AxonTradeMgcNormalBreakEvenBot(SCStudyInterfaceRef sc)
{
    RunMgcNormalBreakEvenStudy(sc);
}

SCSFExport scsf_AxonTradeMnqTopRunnerSimBot(SCStudyInterfaceRef sc)
{
    RunMnqTopRunnerSimStudy(sc);
}
