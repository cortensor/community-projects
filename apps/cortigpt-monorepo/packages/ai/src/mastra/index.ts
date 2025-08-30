import { Mastra } from "@mastra/core/mastra";
import { PinoLogger } from "@mastra/loggers";
import { mkdirSync } from 'fs';
import { dirname } from 'path';
import { cortiGPTAgent } from "./agents/cortigpt-agent";

// // Ensure logs directory exists
// const logPath = 'logs/mastra-debug.log';
// try {
//     mkdirSync(dirname(logPath), { recursive: true });
// } catch (error) {
//     // Directory might already exist, ignore error
// }

// // Configure comprehensive logging for debugging and monitoring
// const logger = new PinoLogger({
//     name: 'Cortensor-Mastra',
//     level: 'debug', // Enable debug level logging for detailed information
//     // Use only console transport for now to avoid file path issues
//     // File logging can be added later with proper path resolution
//     formatters: {
//         level: (label) => {
//             return { level: label.toUpperCase() };
//         },
//         bindings: (bindings) => {
//             return {
//                 pid: bindings.pid,
//                 hostname: bindings.hostname,
//                 name: bindings.name,
//                 timestamp: new Date().toISOString()
//             };
//         }
//     }
// });

export const mastra = new Mastra({
    agents: { cortiGPTAgent },
    

    // Enable OpenAPI documentation for development

});

