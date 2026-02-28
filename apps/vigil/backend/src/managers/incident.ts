import type { Incident, MetricsSnapshot } from '../types/index.js';
import { metricsMonitor } from '../monitors/metrics.js';
import { cortensorClient } from '../detectors/cortensor.js';
import { actionExecutor } from '../actions/executor.js';
import { evidenceBundler } from '../evidence/bundler.js';
import db from '../db/index.js';

export class IncidentManager {
  private activeIncidents: Map<string, Incident> = new Map();

  async processMetrics(metrics: MetricsSnapshot) {
    const anomaly = metricsMonitor.detectAnomalies(metrics);
    
    if (!anomaly.hasAnomaly) return null;

    // Create incident
    const incident: Incident = {
      id: `incident_${Date.now()}`,
      type: anomaly.type as any,
      status: 'detected',
      severity: anomaly.severity as any,
      detectedAt: Date.now(),
      metrics,
      actions: []
    };

    this.activeIncidents.set(incident.id, incident);
    this.saveIncident(incident);

    // Analyze with Cortensor
    incident.status = 'analyzing';
    this.updateIncident(incident);

    const analysis = await cortensorClient.analyzeAnomaly(incident.type, metrics);
    incident.analysis = analysis;

    // Check consensus
    if (analysis.consensus) {
      incident.status = 'confirmed';
      this.updateIncident(incident);

      // Execute actions
      incident.status = 'acting';
      this.updateIncident(incident);

      const actions = await actionExecutor.executeActions(incident);
      incident.actions = actions;

      // Generate evidence bundle
      incident.evidenceBundle = evidenceBundler.generateBundle(incident);
      
      incident.status = 'resolved';
      incident.resolvedAt = Date.now();
      this.updateIncident(incident);
    } else {
      // No consensus, mark as resolved without action
      incident.status = 'resolved';
      incident.resolvedAt = Date.now();
      this.updateIncident(incident);
    }

    return incident;
  }

  getIncident(id: string): Incident | null {
    const stmt = db.prepare('SELECT * FROM incidents WHERE id = ?');
    const row = stmt.get(id) as any;
    return row ? this.rowToIncident(row) : null;
  }

  getAllIncidents(limit = 50): Incident[] {
    const stmt = db.prepare('SELECT * FROM incidents ORDER BY detected_at DESC LIMIT ?');
    const rows = stmt.all(limit) as any[];
    return rows.map(row => this.rowToIncident(row));
  }

  getActiveIncidents(): Incident[] {
    const stmt = db.prepare("SELECT * FROM incidents WHERE status != 'resolved' ORDER BY detected_at DESC");
    const rows = stmt.all() as any[];
    return rows.map(row => this.rowToIncident(row));
  }

  private saveIncident(incident: Incident) {
    const stmt = db.prepare(`
      INSERT INTO incidents (id, type, status, severity, detected_at, metrics, actions)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      incident.id,
      incident.type,
      incident.status,
      incident.severity,
      incident.detectedAt,
      JSON.stringify(incident.metrics),
      JSON.stringify(incident.actions)
    );
  }

  private updateIncident(incident: Incident) {
    const stmt = db.prepare(`
      UPDATE incidents
      SET status = ?, resolved_at = ?, analysis = ?, actions = ?, evidence_bundle = ?
      WHERE id = ?
    `);

    stmt.run(
      incident.status,
      incident.resolvedAt || null,
      incident.analysis ? JSON.stringify(incident.analysis) : null,
      JSON.stringify(incident.actions),
      incident.evidenceBundle ? JSON.stringify(incident.evidenceBundle) : null,
      incident.id
    );
  }

  private rowToIncident(row: any): Incident {
    return {
      id: row.id,
      type: row.type,
      status: row.status,
      severity: row.severity,
      detectedAt: row.detected_at,
      resolvedAt: row.resolved_at,
      metrics: JSON.parse(row.metrics),
      analysis: row.analysis ? JSON.parse(row.analysis) : undefined,
      actions: JSON.parse(row.actions),
      evidenceBundle: row.evidence_bundle ? JSON.parse(row.evidence_bundle) : undefined
    };
  }
}

export const incidentManager = new IncidentManager();
