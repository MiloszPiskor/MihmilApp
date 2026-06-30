import { Outlet, Link as RouterLink } from 'react-router-dom';
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import BusinessOutlinedIcon from '@mui/icons-material/BusinessOutlined';
import { useState } from 'react';

const drawerWidth = 280;

export function MainLayout() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);

  const toggleDrawer = () => {
    setIsDrawerOpen((previous) => !previous);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />
      <AppBar position="fixed" color="inherit" elevation={0}>
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton edge="start" color="inherit" onClick={toggleDrawer} aria-label="open drawer">
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div">
              MihmilApp
            </Typography>
          </Box>
          <Avatar sx={{ bgcolor: 'primary.main' }} alt="User avatar">
            A
          </Avatar>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="persistent"
        open={isDrawerOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            <ListItem disablePadding>
              <ListItemButton component={RouterLink} to="/">
                <ListItemIcon>
                  <BusinessOutlinedIcon color="primary" />
                </ListItemIcon>
                <ListItemText primary="Company Lookup" />
              </ListItemButton>
            </ListItem>
          </List>
          <Divider />
          <Box sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">
              TODO: Add additional navigation entries for Representative Dashboard, Manager Dashboard, and Office Panel.
            </Typography>
          </Box>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
