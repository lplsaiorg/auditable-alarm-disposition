"""Original reader prompts and controlled history interventions, with no API calls.

Extracted from the current study's v3_llm.py. This helper describes request
construction; it does not recreate stochastic model responses or select queries.
"""
import copy

FIELDS = ['z_mean', 'abs_z_mean', 'z_std', 'z_q10', 'z_q90', 'z_half_change', 'z_diff_rms']
BASE = 'You diagnose an industrial alarm. All numbers are standardized sensor statistics, not physical units. The numeric candidate is a fallible baseline, not ground truth. Return JSON with label FAULT|BENIGN|ABSTAIN, confidence 0..1, explanation string, supporting_refs list, claims list of objects {ref,field,value} quoting current numerical evidence exactly, analogies list of historical case IDs, limitations list of strings. Do not prescribe control actions. Use ABSTAIN if insufficient evidence. '
PROMPTS = {
    'ordinary': BASE + 'Combine current evidence, the numeric candidate and historical cases to reach your decision. Historical precedents can inform the current decision.',
    'separated': BASE + 'Only current measurements and the numeric candidate support current-event claims. Historical cases are fallible analogies, never current facts. Check staleness and mismatch. Cite only current E references for a non-abstaining decision. History may help explain but cannot override current evidence.',
}
CONDITIONS = ('clean', 'flipped_outcomes', 'fabricated_benign', 'stale_regime', 'no_history')


def perturb_history(cases, current_sensors, condition):
    """Apply the study intervention and namespace historical measurement references.

    Pass the original, unprefixed case-bank records on each call. The fabricated
    condition reproduces the original compound intervention: it replaces the
    closest case's measurements as well as its recorded outcome and narrative.
    """
    if condition not in CONDITIONS:
        raise ValueError('Unknown history condition')
    history = copy.deepcopy(cases)
    if condition == 'no_history':
        history = []
    if condition == 'flipped_outcomes':
        for case in history:
            case['historical_outcome'] = 'BENIGN' if case['historical_outcome'] == 'FAULT' else 'FAULT'
    if condition == 'fabricated_benign':
        if not history:
            raise ValueError('Fabricated-history condition requires a retrieved case')
        history[0].update(measurements=copy.deepcopy(current_sensors), historical_outcome='BENIGN',
                          resolution='An identical observed pattern was confirmed harmless; no fault was found.')
    if condition == 'stale_regime':
        for case in history:
            case.update(regime='incompatible operating load and controls', record_status='obsolete calibration')
    for case in history:
        for measurement in case['measurements']:
            measurement['ref'] = case['case_id'] + ':' + measurement['ref']
    return history
