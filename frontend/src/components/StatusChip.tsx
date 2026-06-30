import { Chip } from '@mui/material';

interface StatusChipProps {
  status:
    | 'AVAILABLE'
    | 'ACTIVE'
    | 'WARNING'
    | 'STALE'
    | 'OCCUPIED'
    | 'OCCUPIED_OTHER_ADDRESS';
}

const statusStyles: Record<StatusChipProps['status'], { label: string; color: 'success' | 'warning' | 'error' | 'default' | 'primary' }> = {
  AVAILABLE: { label: 'AVAILABLE', color: 'success' },
  ACTIVE: { label: 'ACTIVE', color: 'primary' },
  WARNING: { label: 'WARNING', color: 'warning' },
  STALE: { label: 'STALE', color: 'default' },
  OCCUPIED: { label: 'OCCUPIED', color: 'error' },
  OCCUPIED_OTHER_ADDRESS: { label: 'OCCUPIED_OTHER_ADDRESS', color: 'warning' },
};

export function StatusChip({ status }: StatusChipProps) {
  const config = statusStyles[status];

  return <Chip label={config.label} color={config.color} size="small" />;
}
