/**
 * ViewToggle - Clean segmented control for switching evidence views
 */

import { ViewRole } from '../api';

interface ViewToggleProps {
    value: ViewRole;
    onChange: (role: ViewRole) => void;
    disabled?: boolean;
}

const roles: { value: ViewRole; label: string; icon: string }[] = [
    { value: 'voter', label: 'Voter', icon: '🗳️' },
    { value: 'delegate', label: 'Delegate', icon: '📊' },
    { value: 'auditor', label: 'Auditor', icon: '🔬' },
];

export const ViewToggle = ({ value, onChange, disabled }: ViewToggleProps) => {
    return (
        <div
            className="inline-flex rounded-lg overflow-hidden p-1"
            style={{
                background: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
            }}
        >
            {roles.map((role) => {
                const isActive = value === role.value;
                return (
                    <button
                        key={role.value}
                        onClick={() => onChange(role.value)}
                        disabled={disabled}
                        className={`
                            flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium
                            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                        style={{
                            background: isActive ? 'var(--color-accent)' : 'transparent',
                            color: isActive ? 'white' : 'var(--color-text-secondary)',
                        }}
                    >
                        <span>{role.icon}</span>
                        <span>{role.label}</span>
                    </button>
                );
            })}
        </div>
    );
};

export default ViewToggle;
