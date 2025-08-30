import { PromptBuilder } from '../types';
import { LlavaPromptBuilder } from './LlavaPromptBuilder';
import { DeepSeekPromptBuilder } from './DeepSeekPromptBuilder';
import { LlamaPromptBuilder } from './LlamaPromptBuilder';

export class PromptBuilderFactory {
  private static builders: Map<string, PromptBuilder> = new Map();

  static {
    // Initialize all prompt builders
    const llavaBuilder = new LlavaPromptBuilder();
    const deepSeekBuilder = new DeepSeekPromptBuilder();
    const llamaBuilder = new LlamaPromptBuilder();

    this.builders.set(llavaBuilder.getModelId(), llavaBuilder);
    this.builders.set(deepSeekBuilder.getModelId(), deepSeekBuilder);
    this.builders.set(llamaBuilder.getModelId(), llamaBuilder);
  }

  /**
   * Get a prompt builder for the specified model
   */
  static getBuilder(modelId: string): PromptBuilder | null {
    return this.builders.get(modelId) || null;
  }

  /**
   * Get all available prompt builders
   */
  static getAllBuilders(): PromptBuilder[] {
    return Array.from(this.builders.values());
  }

  /**
   * Register a new prompt builder
   */
  static registerBuilder(builder: PromptBuilder): void {
    this.builders.set(builder.getModelId(), builder);
  }

  /**
   * Check if a model has a prompt builder
   */
  static hasBuilder(modelId: string): boolean {
    return this.builders.has(modelId);
  }

  /**
   * Get default prompt builder (fallback)
   */
  static getDefaultBuilder(): PromptBuilder {
    return this.builders.get('llava-v1') || new LlavaPromptBuilder();
  }
}