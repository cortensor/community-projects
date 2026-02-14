import { generalAssistant } from "./generalAssistant";
import { businessPlanner } from "./businessPlanner";
import { textSummarizer } from "./textSummarizer";
import { insightAnalyzer } from "./insightAnalyzer";
import { formatConverter } from "./formatConverter";

export const agentFunctions = {
  "💬 General Assistant": generalAssistant,
  "💼 Business Planner": businessPlanner,
  "📝 Text Summarizer": textSummarizer,
  "📊 Insight Analyzer": insightAnalyzer,
  "🔄 Format Converter": formatConverter
};
