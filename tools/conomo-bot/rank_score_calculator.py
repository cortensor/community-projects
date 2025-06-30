# import math, sys
from datetime import datetime, timezone
from Metric import Metric

global_stats = {
    "maxPrecommitCounter": 0,
    "maxCommitCounter": 0,
    "maxPrepareCounter": 0,
    "minPrecommitCounter": float("inf"),
    "minCommitCounter": float("inf"),
    "minPrepareCounter": float("inf"),
    "initialized": False
}


def get_metric_by_name(metrics: list[Metric], name: str):
    return next((m for m in metrics if m.name == name), None)


def update_global_stats(all_nodes_metrics: list[list[Metric]]):
    if not all_nodes_metrics:
        return

    global global_stats
    global_stats = {
        "maxPrecommitCounter": 0,
        "maxCommitCounter": 0,
        "maxPrepareCounter": 0,
        "minPrecommitCounter": float("inf"),
        "minCommitCounter": float("inf"),
        "minPrepareCounter": float("inf"),
        "initialized": True
    }

    for metrics in all_nodes_metrics:
        metric = get_metric_by_name(metrics, "Precommit")
        if metric is not None:
            global_stats["maxPrecommitCounter"] = max(global_stats["maxPrecommitCounter"], metric.counter)
            global_stats["minPrecommitCounter"] = min(global_stats["minPrecommitCounter"], metric.counter)

        metric = get_metric_by_name(metrics, "Commit")
        if metric is not None:
            global_stats["maxCommitCounter"] = max(global_stats["maxCommitCounter"], metric.counter)
            global_stats["minCommitCounter"] = min(global_stats["minCommitCounter"], metric.counter)

        metric = get_metric_by_name(metrics, "Prepare")
        if metric is not None:
            global_stats["maxPrepareCounter"] = max(global_stats["maxPrepareCounter"], metric.counter)
            global_stats["minPrepareCounter"] = min(global_stats["minPrepareCounter"], metric.counter)

    if global_stats["minPrecommitCounter"] == float("inf"):
        global_stats["minPrecommitCounter"] = 0
    if global_stats["minCommitCounter"] == float("inf"):
        global_stats["minCommitCounter"] = 0
    if global_stats["minPrepareCounter"] == float("inf"):
        global_stats["minPrepareCounter"] = 0


def calculate_rank_score(metrics: list[Metric]):
    metric_last_active = get_metric_by_name(metrics, "Last Active")
    metric_precommit = get_metric_by_name(metrics, "Precommit")
    
    if not metric_precommit or not metric_precommit.counter or not metric_last_active.counter:
        return 0.0

    now = int(datetime.now(timezone.utc).timestamp())
    inactive_minutes = (now - metric_last_active.counter) / 60

    if inactive_minutes <= 5:
        activity_score = 1.0
    elif inactive_minutes <= 15:
        activity_score = 1.0 - (0.5 * ((inactive_minutes - 5) / 10))
    elif inactive_minutes <= 30:
        activity_score = 0.5 - (0.3 * ((inactive_minutes - 15) / 15))
    elif inactive_minutes <= 60:
        activity_score = 0.2 - (0.15 * ((inactive_minutes - 30) / 30))
    elif inactive_minutes <= 240:
        activity_score = 0.05 - (0.04 * ((inactive_minutes - 60) / 180))
    else:
        activity_score = 0.0

    metric_prepare = get_metric_by_name(metrics, "Prepare")
    metric_commit = get_metric_by_name(metrics, "Commit")

    precommit_success = metric_precommit.points / metric_precommit.counter if metric_precommit.counter> 0 else 0
    prepare_success = metric_prepare.points / metric_prepare.counter if metric_prepare.counter> 0 else 0
    commit_success = metric_commit.points / metric_commit.counter if metric_commit.counter> 0 else 0

    def penalize_failing_node(success_rate, successes, attempts):
        if not attempts:
            return 0

        failures = attempts - successes
        failure_rate = 1 - success_rate
        penalty = success_rate

        if success_rate < 0.6:
            quadratic_penalty = (0.6 - success_rate) ** 2 * 2.5
            penalty *= (1 - quadratic_penalty)
        if success_rate < 0.3:
            penalty *= (success_rate * 2)
        if failures > 10:
            failure_penalty_factor = min(0.9, failures / 100)
            penalty *= (1 - failure_penalty_factor)
        if failure_rate > 0.8:
            penalty *= (0.2 - (failure_rate - 0.8))
        if success_rate <= 0 or penalty <= 0:
            return 0.001
        return max(0.01, penalty)

    adjusted_precommit = penalize_failing_node(precommit_success, metric_precommit.points, metric_precommit.counter)
    adjusted_commit = penalize_failing_node(commit_success, metric_commit.points, metric_commit.counter)

    has_prepare_data = metric_prepare.counter > 0
    has_commit_data = metric_commit.counter > 0

    precommit_commit_pair = (adjusted_precommit + adjusted_commit) / 2 if has_commit_data else adjusted_precommit
    success_rate = precommit_commit_pair

    if has_prepare_data and prepare_success > 0.6:
        bonus = ((prepare_success - 0.6) ** 2) * 0.3
        success_rate = min(1, success_rate + bonus)

    if precommit_success < 0.6:
        deficit = 0.6 - precommit_success
        if precommit_success < 0.3:
            severity = 0.8 + 0.19 * (1 - precommit_success / 0.3)
            success_rate *= (1 - severity)
        else:
            penalty_factor = min(0.95, deficit ** 2 * 8)
            success_rate *= (1 - penalty_factor)

    def calc_counter_weight(counter, max_counter):
        if not counter:
            return 0
        percentile = counter / max_counter
        if percentile < 0.05:
            return percentile * 0.4
        elif percentile < 0.2:
            return 0.02 + (percentile - 0.05) * 0.6
        elif percentile < 0.5:
            return 0.11 + (percentile - 0.2) * 0.9
        else:
            return 0.38 + (percentile - 0.5) * 1.24

    pcw = calc_counter_weight(metric_precommit.counter, global_stats["maxPrecommitCounter"])
    prcw = calc_counter_weight(metric_prepare.counter, global_stats["maxPrepareCounter"]) if has_prepare_data else 0
    ccw = calc_counter_weight(metric_commit.counter, global_stats["maxCommitCounter"]) if has_commit_data else 0

    precommit_commit_counter_weight = (pcw + ccw) / 2 if has_commit_data else pcw
    counter_weight = 0.3 * prcw + 0.7 * precommit_commit_counter_weight if has_prepare_data else precommit_commit_counter_weight

    if precommit_success == 1 and (not has_commit_data or commit_success == 1) and (not has_prepare_data or prepare_success == 1) and (not has_commit_data or metric_commit.counter == metric_precommit.counter):
        counter_weight = max(counter_weight, 0.95)

    if has_commit_data and metric_precommit.counter > 0:
        ratio = metric_commit.counter / metric_precommit.counter
        if ratio < 0.95:
            penalty = (1 - ratio) ** 2
            success_rate *= (1 - penalty)

    activity_weight, success_weight, counter_weight_val = 0.1, 0.5, 0.4

    if inactive_minutes > 15:
        if inactive_minutes <= 30:
            activity_weight, success_weight, counter_weight_val = 0.2, 0.5, 0.3
        elif inactive_minutes <= 60:
            activity_weight, success_weight, counter_weight_val = 0.4, 0.3, 0.3
        elif inactive_minutes <= 240:
            activity_weight, success_weight, counter_weight_val = 0.6, 0.2, 0.2
        else:
            activity_weight, success_weight, counter_weight_val = 0.9, 0.05, 0.05

    final_score = (success_weight * success_rate) + (counter_weight_val * counter_weight) + (activity_weight * activity_score)

    def apply_counter_cap(score):
        percentile = metric_precommit.counter / global_stats["maxPrecommitCounter"]
        if percentile < 0.01:
            return min(score, 0.4 + percentile * 10)
        elif percentile < 0.05:
            return min(score, 0.5 + (percentile - 0.01) * 2.5)
        elif percentile < 0.2:
            return min(score, 0.6 + (percentile - 0.05) * 1.33)
        elif percentile < 0.5:
            return min(score, 0.8 + (percentile - 0.2) * 0.33)
        elif percentile < 0.8:
            return min(score, 0.9 + (percentile - 0.5) * 0.17)
        return score

    final_score = apply_counter_cap(final_score)

    if precommit_success == 1 and (not has_commit_data or commit_success == 1) and (not has_prepare_data or prepare_success == 1) and (not has_commit_data or metric_commit.counter == metric_precommit.counter) and inactive_minutes <= 5:
        percentile = metric_precommit.counter / global_stats["maxPrecommitCounter"]
        if percentile >= 0.8:
            final_score = 1.0
        elif percentile >= 0.5:
            final_score = min(0.9 + (percentile - 0.5) * 0.17, final_score)
        elif percentile >= 0.2:
            final_score = min(0.8 + (percentile - 0.2) * 0.33, final_score)
        elif percentile >= 0.05:
            final_score = min(0.6 + (percentile - 0.05) * 1.33, final_score)
        elif percentile >= 0.01:
            final_score = min(0.5 + (percentile - 0.01) * 2.5, final_score)
        else:
            final_score = min(0.4 + percentile * 10, final_score)

    return round(final_score, 2)


def get_node_color_by_score(score):
    if score >= 0.95:
        return "#2196f3"
    elif score >= 0.9:
        return "#00bcd4"
    elif score >= 0.8:
        return "#4caf50"
    elif score >= 0.7:
        return "#66bb6a"
    elif score >= 0.6:
        return "#8bc34a"
    elif score >= 0.5:
        return "#cddc39"
    elif score >= 0.4:
        return "#ff9800"
    elif score >= 0.2:
        return "#ff5722"
    elif score >= 0:
        return "#f44336"
    return "#cccccc"

def get_rank_status_by_score(score):
    if score >= 0.95:
        return {"status": "Elite", "color": "#2196f3"}
    elif score >= 0.9:
        return {"status": "Exceptional", "color": "#00bcd4"}
    elif score >= 0.8:
        return {"status": "Excellent", "color": "#4caf50"}
    elif score >= 0.7:
        return {"status": "Very Good", "color": "#66bb6a"}
    elif score >= 0.6:
        return {"status": "Good", "color": "#8bc34a"}
    elif score >= 0.5:
        return {"status": "Above Average", "color": "#cddc39"}
    elif score >= 0.4:
        return {"status": "Average", "color": "#ff9800"}
    elif score >= 0.2:
        return {"status": "Below Average", "color": "#ff5722"}
    elif score >= 0:
        return {"status": "Poor", "color": "#f44336"}
    return {"status": "No Data", "color": "#cccccc"}