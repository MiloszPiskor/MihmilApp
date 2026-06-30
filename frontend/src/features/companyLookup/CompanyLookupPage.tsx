import { Container, Paper, Typography, Box } from '@mui/material';
import { CompanyLookupForm } from './components/CompanyLookupForm';
import { CompanyLookupErrorAlert } from './components/CompanyLookupErrorAlert';
import { CompanyLookupResultCard } from './components/CompanyLookupResultCard';
import { useCompanyLookup } from './hooks/useCompanyLookup';

export function CompanyLookupPage() {
  const { isLoading, response, fieldErrors, serverError, search } = useCompanyLookup();

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Company Lookup
        </Typography>
        <Typography color="text.secondary">
          Search for company address availability and representative assignment.
        </Typography>
      </Box>
      <Paper sx={{ p: 3, mb: 4 }}>
        <CompanyLookupForm
          isLoading={isLoading}
          fieldErrors={fieldErrors}
          onSubmit={search}
        />
      </Paper>
      {serverError && <CompanyLookupErrorAlert message={serverError} />}
      {response && <CompanyLookupResultCard result={response} />}
      <Box sx={{ mt: 4 }}>
        <Typography variant="body2" color="text.secondary">
          TODO: Implement Representative Dashboard, Manager Dashboard, and Office Panel pages.
        </Typography>
      </Box>
    </Container>
  );
}
