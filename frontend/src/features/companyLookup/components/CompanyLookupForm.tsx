import { useState } from 'react';
import {
  Button,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { CompanyLookupRequest } from '../types';

interface CompanyLookupFormProps {
  isLoading: boolean;
  fieldErrors: Partial<Record<keyof CompanyLookupRequest, string>>;
  onSubmit: (payload: CompanyLookupRequest) => Promise<void>;
}

const initialFormState: CompanyLookupRequest = {
  nip: '',
  street: '',
  building_nr: '',
  postal_code: '',
  city: '',
};

export function CompanyLookupForm({ isLoading, fieldErrors, onSubmit }: CompanyLookupFormProps) {
  const [formState, setFormState] = useState<CompanyLookupRequest>(initialFormState);

  const handleChange = (field: keyof CompanyLookupRequest) => (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setFormState((previous) => ({
      ...previous,
      [field]: event.target.value,
    }));
  };

const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {

  event.preventDefault();

  console.log("SUBMIT");

  console.log(formState);

  await onSubmit(formState);

};

  return (
    <form noValidate onSubmit={handleSubmit}>
      <Stack spacing={3}>
        <Typography variant="subtitle1">Enter company address details</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="NIP"
              name="nip"
              value={formState.nip}
              onChange={handleChange('nip')}
              error={Boolean(fieldErrors.nip)}
              helperText={fieldErrors.nip}
              disabled={isLoading}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Street"
              name="street"
              value={formState.street}
              onChange={handleChange('street')}
              error={Boolean(fieldErrors.street)}
              helperText={fieldErrors.street}
              disabled={isLoading}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Building number"
              name="building_nr"
              value={formState.building_nr}
              onChange={handleChange('building_nr')}
              error={Boolean(fieldErrors.building_nr)}
              helperText={fieldErrors.building_nr}
              disabled={isLoading}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Postal code"
              name="postal_code"
              value={formState.postal_code}
              onChange={handleChange('postal_code')}
              error={Boolean(fieldErrors.postal_code)}
              helperText={fieldErrors.postal_code}
              disabled={isLoading}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="City"
              name="city"
              value={formState.city}
              onChange={handleChange('city')}
              error={Boolean(fieldErrors.city)}
              helperText={fieldErrors.city}
              disabled={isLoading}
            />
          </Grid>
        </Grid>
        <Button type="submit" variant="contained" color="primary" disabled={isLoading} size="large">
          {isLoading ? <CircularProgress size={24} color="inherit" /> : 'Search'}
        </Button>
      </Stack>
    </form>
  );
}
