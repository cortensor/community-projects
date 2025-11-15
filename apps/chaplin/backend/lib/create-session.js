// create-session.js
import CortensorModel from './models/CortensorModel.js'; // Ajuste o caminho
import dotenv from 'dotenv';
dotenv.config();

async function main() {
    console.log("Attempting to create a new Cortensor session...");
    try {
        const model = new CortensorModel();
        const sessionId = await model.createSession();
        console.log("\n------------------------------------------------------");
        console.log("✅ Session created successfully!");
        console.log(`   Session ID: ${sessionId}`);
        console.log("   Add this line to your .env file:");
        console.log(`CORTENSOR_SESSION_ID=${sessionId}`);
        console.log("------------------------------------------------------\n");
    } catch (error) {
        console.error("❌ Failed to create session:", error);
    }
}

main();