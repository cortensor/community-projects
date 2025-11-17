CortensorPulse - Hackathon #2 Submission

CortensorPulse is a backend-less, real-time observability dashboard for the Cortensor decentralized inference network. It connects directly to the official network API to provide live stats on node performance and health.

✨ Features

"At a Glance" Summary Cards: Instantly view high-level network health:

Total Active Nodes

Average Total Score (Qualitative)

Average Level (Quantitative)

Interactive Node Leaderboard: A fully searchable and sortable table of all active nodes.

Live Search & Filter: Instantly filter the entire list by a node's wallet address as you type.

One-Click Sorting: Re-order the leaderboard by Official Rank or by Total Score (high to low).

"Node Detail" Modal: Click any node to open a pop-up with granular, "deep-dive" stats, including all cognitive points, timestamps, and quantitative data.

100% Live Data: Connects directly to the official Cortensor Dashboard API (https://db-be-7.cortensor.network/leaderboard) for real-time data.

🚀 Getting Started

This project is a 100% frontend application and does not require a separate backend.

Prerequisites

Node.js (v18 or later)

npm (comes with Node.js)

Installation

Clone the repository:

git clone [https://github.com/Sanjugupta21/cortensor-pulse.git](https://github.com/Sanjugupta21/cortensor-pulse.git)


Navigate to the project directory:

cd cortensor-pulse


Install the project dependencies:

npm install


Install the icon library (if not already in package.json):

npm install lucide-react


Usage

Once the installation is complete, run the development server:

npm run dev


This will automatically open the dashboard in your browser, usually at http://localhost:5173. The app will fetch live data from the Cortensor network immediately.

👤 Maintainer

Gupta Sanju Babul

🤝 Contributing

Contributions are welcome! Please feel free to fork the repository and submit a Pull Request.

📄 License

This project is licensed under the MIT License.