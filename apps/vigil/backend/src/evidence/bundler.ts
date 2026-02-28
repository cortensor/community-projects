import type { Incident, EvidenceBundle, TimelineEvent } from '../types/index.js';

export class EvidenceBundler {
  generateBundle(incident: Incident): EvidenceBundle {
    const timeline = this.buildTimeline(incident);

    return {
      incidentId: incident.id,
      timestamp: Date.now(),
      metrics: incident.metrics,
      analysis: incident.analysis!,
      actions: incident.actions,
      timeline
    };
  }

  private buildTimeline(incident: Incident): TimelineEvent[] {
    const timeline: TimelineEvent[] = [
      {
        timestamp: incident.detectedAt,
        event: 'Incident Detected',
        details: { type: incident.type, severity: incident.severity }
      }
    ];

    if (incident.analysis) {
      timeline.push({
        timestamp: incident.analysis.timestamp,
        event: 'Analysis Completed',
        details: {
          consensus: incident.analysis.consensus,
          confidence: incident.analysis.confidence,
          models: incident.analysis.modelOutputs.length
        }
      });
    }

    incident.actions.forEach(action => {
      timeline.push({
        timestamp: action.timestamp,
        event: `Action: ${action.type}`,
        details: { status: action.status, result: action.result }
      });
    });

    if (incident.resolvedAt) {
      timeline.push({
        timestamp: incident.resolvedAt,
        event: 'Incident Resolved',
        details: { duration: incident.resolvedAt - incident.detectedAt }
      });
    }

    return timeline.sort((a, b) => a.timestamp - b.timestamp);
  }

  exportToJSON(bundle: EvidenceBundle): string {
    return JSON.stringify(bundle, null, 2);
  }
}

export const evidenceBundler = new EvidenceBundler();
