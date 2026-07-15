# Current Vissim object inventory

Source network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`

Generated artifacts:

- `inventory.json`: full parsed object inventory
- `network_mapping.json`: draft link/connector/control mapping
- `missing_objects.json`: objects required before full controller evaluation
- `links.csv`: road-link table
- `connectors.csv`: connector table

Summary:

- Road links: 34
- Connectors: 74
- Total link objects: 108
- Vehicle inputs: 9
- Data collection points: 64
- Queue counters: 23
- Static route decisions: 0
- Static routes: 0
- Signal controllers: 0
- Signal heads: 0
- Nodes: 8

Important interpretation:

- Detector-style measurements already exist in a useful form: 64 data collection points and 23 queue counters.
- Route decisions are missing, so OD-controlled demand assignment must be added before meaningful travel-time/controller evaluation.
- Signal objects are missing, so the first runnable controller connection is global-state logging/no-op. Fixed-time and adaptive control require signal controllers/heads in an evaluation copy.
