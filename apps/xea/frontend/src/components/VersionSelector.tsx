/**
 * VersionSelector - Dropdown to switch between proposal versions
 */

import { ProposalVersion } from '../api';

interface VersionSelectorProps {
    versions: ProposalVersion[];
    currentVersion: number;
    onChange: (version: ProposalVersion) => void;
}

export const VersionSelector = ({ versions, currentVersion, onChange }: VersionSelectorProps) => {
    if (versions.length <= 1) {
        return null; // Don't show if only one version
    }

    return (
        <div className="inline-flex items-center gap-2">
            <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Version:
            </span>
            <select
                value={currentVersion}
                onChange={(e) => {
                    const version = versions.find(v => v.version_number === Number(e.target.value));
                    if (version) onChange(version);
                }}
                className="px-3 py-1.5 rounded-lg text-sm font-medium"
                style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                }}
            >
                {versions.map((v) => (
                    <option key={v.version_number} value={v.version_number}>
                        v{v.version_number} {v.version_number === versions[versions.length - 1]?.version_number ? '(latest)' : ''}
                    </option>
                ))}
            </select>
        </div>
    );
};

export default VersionSelector;
