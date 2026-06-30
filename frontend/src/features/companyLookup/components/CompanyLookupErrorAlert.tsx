import { Alert, AlertTitle, Box } from '@mui/material';

interface CompanyLookupErrorAlertProps {
  message: string;
}

export function CompanyLookupErrorAlert({ message }: CompanyLookupErrorAlertProps) {
  return (
    <Box sx={{ mb: 3 }}>
      <Alert severity="error">
        <AlertTitle>Error</AlertTitle>
        {message}
      </Alert>
    </Box>
  );
}
