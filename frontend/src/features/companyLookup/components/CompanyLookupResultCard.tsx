import {
  Card,
  CardContent,
  Stack,
  Typography,
  Grid,
  Box,
} from '@mui/material';
import type {
  CompanyLookupAvailableDto,
  CompanyLookupOccupiedDto,
  CompanyLookupOtherAddressDto,
} from '../types';
import { StatusChip } from '../../../components/StatusChip';

type CompanyLookupSuccessDto =
  | CompanyLookupAvailableDto
  | CompanyLookupOccupiedDto
  | CompanyLookupOtherAddressDto;

interface CompanyLookupResultCardProps {
  result: CompanyLookupSuccessDto;
}

function renderAvailable(result: CompanyLookupAvailableDto) {
  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Message
      </Typography>
      <Typography>{result.message}</Typography>
    </Box>
  );
}

function renderOccupied(result: CompanyLookupOccupiedDto) {
  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Company
      </Typography>
      <Typography>{result.company_name}</Typography>
      <Typography>{`${result.street} ${result.building_nr}`}</Typography>
      <Typography>{`${result.postal_code} ${result.city}`}</Typography>
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2">Assigned representative</Typography>
        <Typography>{result.assigned_rep_name}</Typography>
        <Typography>{result.assigned_rep_reference}</Typography>
      </Box>
    </Box>
  );
}

function renderOtherAddress(result: CompanyLookupOtherAddressDto) {
  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1">Occupied addresses</Typography>
      <Grid container spacing={2}>
        {result.occupied_addresses.map((address, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2">{address.company_name}</Typography>
                <Typography>{`${address.street} ${address.building_nr}`}</Typography>
                <Typography>{`${address.postal_code} ${address.city}`}</Typography>
                {address.assigned_rep_name ? (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="subtitle2">Assigned representative</Typography>
                    <Typography>{address.assigned_rep_name}</Typography>
                  </Box>
                ) : null}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}

export function CompanyLookupResultCard({ result }: CompanyLookupResultCardProps) {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
            <Typography variant="h6">Company lookup result</Typography>
            <StatusChip status={result.status} />
          </Stack>
          <Box sx={{ mt: 3 }}>
            {result.status === 'AVAILABLE' && renderAvailable(result)}
            {result.status === 'OCCUPIED' && renderOccupied(result)}
            {result.status === 'OCCUPIED_OTHER_ADDRESS' && renderOtherAddress(result)}
          </Box>
        </CardContent>
      </Card>
    </Stack>
  );
}
