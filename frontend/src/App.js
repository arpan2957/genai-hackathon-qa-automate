
import React, { useState, useEffect } from 'react';
import { auth } from './firebase';

import AppPage from './pages/AppPage';
import WelcomePage from './pages/WelcomePage';

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(user => {
      setUser(user);
      if (user) {
        setShowLogin(false);
      }
      setAuthLoading(false);
    });
    return unsubscribe;
  }, []);

  if (authLoading) {
    return <div>Loading Application...</div>; 
  }

  return user ? <AppPage /> : <WelcomePage showLogin={showLogin} setShowLogin={setShowLogin} />;
}

export default App;
