import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:3001/api';

export function useIncidents() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);

  const fetchIncidents = async () => {
    try {
      const response = await fetch(`${API_URL}/incidents`);
      const data = await response.json();
      setIncidents(data);
    } catch (error) {
      console.error('Failed to fetch incidents:', error);
    }
  };

  const simulateIncident = async (type: string) => {
    setIsSimulating(true);
    try {
      await fetch(`${API_URL}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
      
      // Wait a bit for the incident to be processed
      setTimeout(() => {
        fetchIncidents();
        setIsSimulating(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to simulate incident:', error);
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  return { incidents, simulateIncident, isSimulating };
}
