import { Route, Routes, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { CompanyLookupPage } from './features/companyLookup/CompanyLookupPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<CompanyLookupPage />} />
        <Route path="*" element={<Navigate replace to="/" />} />
      </Route>
    </Routes>
  );
}

export default App;
