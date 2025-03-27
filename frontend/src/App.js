import React, { useState, useRef } from 'react';
import { Drawer, Button, List, ListItem, ListItemText, Divider } from '@mui/material';
import ForceGraph3D from 'react-force-graph-3d';
import './App.css';

const App = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const graphRef = useRef();

  const toggleDrawer = (open) => (event) => {
    if (event.type === 'keydown' && (event.key === 'Tab' || event.key === 'Shift')) {
      return;
    }
    setDrawerOpen(open);
  };

  const fetchGraphData = async () => {
    const response = await fetch('/graph-data');
    const data = await response.json();
    setGraphData(data);
  };

  React.useEffect(() => {
    fetchGraphData();
  }, []);

  return (
    <div className="App">
      <Button onClick={toggleDrawer(true)}>Open Drawer</Button>
      <Drawer anchor="left" open={drawerOpen} onClose={toggleDrawer(false)}>
        <div
          role="presentation"
          onClick={toggleDrawer(false)}
          onKeyDown={toggleDrawer(false)}
        >
          <List>
            <ListItem button>
              <ListItemText primary="Toggle Links" />
            </ListItem>
            <ListItem button>
              <ListItemText primary="Change Node Color" />
            </ListItem>
          </List>
          <Divider />
        </div>
      </Drawer>
      <div id="3d-graph">
        <ForceGraph3D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="name"
          nodeAutoColorBy="id"
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.006}
          onNodeClick={(node) => {
            const distance = 40;
            const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
            graphRef.current.cameraPosition(
              { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
              node,
              3000
            );
          }}
        />
      </div>
    </div>
  );
};

export default App;