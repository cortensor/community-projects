[![N|Solid](https://i.imgur.com/ESdUHmB.png)](https://chaplin.lumitylabs.com)
# Chaplin
###### _Unleashing the future of AI together - Cortensor Hackathon, 2025_  
### The Specialist Agent Factory | [Try Chaplin Live](https://chaplin.lumitylabs.com/)
"Transform any task into an AI-powered solution. Simply describe what you need, and Chaplin creates and deploys a team of specialist agents that collaborate to accomplish the task. You get a ready-to-use Chaplin that you can share or integrate into your projects."

## 📖 Quick Index
- [🔎 Why?](#-why)
- [💡 How does it Work?](#-how-does-it-work)
- [🎥 Demo](#-demo)
- [🔌 API Integration](#-api-integration)
- [🔧 Technologies](#-technologies)
- [💿 Installation](#-installation)
- [🤝 How to Contribute](#-how-to-contribute)
- [🐞 Report Bug and Errors](#-report-bug-and-errors)
- [📧 Contact](#-contact)

## 🔎 Why? 
AI model responses are significantly improved when provided with relevant context to solve a task. However, each task requires a different type of context, and finding a good solution often involves connecting knowledge from different domains. Creating prompts with this level of depth is a laborious and time-consuming process. This is where Chaplin comes in, addressing several key challenges in using LLMs today:

🎯 __Lack of quality context__  
🎯 __Inconsistent, generic, or repetitive responses__  
🎯 __Frequent occurrence of hallucinations__  
🎯 __The difficulty and high time-cost of generating quality prompts that are dynamic, personalized, and scalable;__  
🎯 __Integration barriers with other systems__

## 💡 How does it Work?  
Chaplin is an AI agent orchestrator that allows you to create and manage specialized teams to solve complex tasks. Each agent acts as an expert in its field, processing information sequentially until the final answer is generated. With a flexible architecture, Chaplins are easy to share, test, and integrate into your projects, making them ideal for a wide range of applications.

## 🎥 Demo
[![Video Demo](https://i.imgur.com/zF0PInT.png)](https://www.youtube.com/watch?v=NiQcVNkmDac)

## 🔌 API Integration
### **How to Integrate with the Chaplin API**  

1.  **Find your Chaplin ID:** After creating or selecting a Chaplin in the web interface, click the **API** button. This will reveal your unique `chaplin_id`.
2.  **View Examples:** In the same popup, you will find code examples for **Python**, **JavaScript**, and **cURL (CLI)** to get you started quickly.
3. The body of your request must be a JSON object containing two keys:
```json
{
  "chaplin_id": "YOUR_CHAPLIN_ID_HERE",
  "input": "Your text or prompt here"
}
```
### **Live Integration Example**  
You can find a demo project that uses the Chaplin API in the `/examples/web3museum` directory.
- View the __Web3Museum__ live demo - **[click here](https://web3museum.lumitylabs.com/)**


## 🔧 Technologies

<p align="left">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=js,react,tailwind,vercel,cloudflare,firebase" />
  </a>
</p>

<details>
  <summary><b>Click to view the full tech stack 🧰 </b></summary>
  <ul>
    <li><strong>Frontend:</strong> JavaScript, React, Tailwind CSS</li>
    <li><strong>Backend:</strong> Vercel Functions, Cloudflare Workers</li>
    <li><strong>Database & Infrastructure:</strong> Firebase, Upstash (QStash), ImgBB</li>
    <li><strong>Authentication:</strong> Clerk</li>
    <li><strong>IA:</strong> LLM (via Cortensor e Gemini)</li>
    <li><strong>Blockchain:</strong> Alchemy, Cortensor</li>
  </ul>
</details>

## 💿 Installation

<details>
  <summary><strong>Step 1 - ✅ Requirements</strong></summary>

#### 
  Before you begin, make sure you have __installed__:  
  - Node.js - **[click here](https://nodejs.org/)**
  - Vercel CLI - **[click here](https://vercel.com/docs/cli)**

  And __have an account__ on the following platforms: 
  - Firebase - **[click here](https://firebase.google.com/)**, 
  - Cloudflare - **[click here](https://dash.cloudflare.com/sign-up/workers-and-pages)**,
  - Alchemy - **[click here](https://www.alchemy.com/)**, 
  - ImgBB - **[click here](https://imgbb.com/)** 
  - Upstash **[click here](https://upstash.com/)**.
#### 

</details>

<details>
  <summary><strong>Step 2 - 🔑 Environment Configuration</strong></summary>

#### 
  - Rename the `.env.example` files to `.env` in the following folders:

    ```
    /backend
    /web
    /examples/web3museum
    ```  
  - Then, open each `.env` file and fill in the environment variables as indicated in the comments.
  ###### **⚠️ Remember to remove the `{` `}` brackets, using only the values as indicated.**
#### 

</details>

<details>
  <summary><strong>Step 3 - 📦 Install Dependencies</strong></summary>

#### 
  - Inside each of the folders below:  

    ```
    /backend
    /web
    /examples/web3museum
    ```  
  - run the command:  

    ```bash
    npm install
    ```
#### 

</details>


<details>
  <summary><strong><b>Step 4</b> - 🚀 Running the Project</strong></summary>
  
#### ⚡ Backend - [http://localhost:3000](http://localhost:3000)  

```bash
cd backend
vercel dev
```

#### 💻 Frontend - [http://localhost:5173](http://localhost:5173)  

```bash
cd web
npm run dev
```

#### 🖼️ Example Web3Museum - [http://localhost:5174](http://localhost:5174)  

```bash
cd examples/web3museum
npm run dev
```
</details>

## 🤝 How to Contribute
- __Integrate Chaplin__ with other systems, tools, or applications
- __Create New Chaplins__ for the community - [**click here**](https://chaplin.lumitylabs.com/create)

## 🐞 Report Bug and Errors  
Found a bug or encountered an error? We'd love to help! Here’s how you can get support:

**Create a GitHub Issue**  
- For well-defined bugs, errors, or feature requests, creating an issue is the best way to ensure it gets tracked and addressed by the team.  
  ➡️ **[Create a new issue here](https://github.com/lumitylabs/chaplin/issues/new)**

**Ask on our Discord**  
- If you're not sure if it's a bug, have a quick question, or want to discuss the issue first, our community on Discord is the perfect place.  
  ➡️ **[Join the discussion on Discord](https://discord.com/channels/1174034150462861324/1433186185253093517)**

## 📧 Contact
If you have any questions or suggestions,  please feel free to contact us. : )

| Contact | Luciano Barros |
| ------ | ------ |
| Discord | @lucianofbn |
| Email | lucianofbn@lumitylabs.com |
| X | @lucianofbn |

| Contact | Rafael Souza | 
| ------ | ------ |
| Discord | @rafaelsouza |
| Email | rafaelsouza@lumitylabs.com |
| X | @rafaelszc |

<br><br>

<p align="center">
  <i>Powered by </i><b><a href="https://www.lumitylabs.com">Lumity</a>💫</b>
</p>
