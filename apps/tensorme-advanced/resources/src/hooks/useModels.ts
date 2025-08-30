"use client";
import { useState, useEffect } from 'react';
import { getClientModels } from '@/lib/models';

export interface Model {
  id: string;
  name: string;
  description?: string;
}

export const useModels = () => {
  const [models] = useState<Model[]>(getClientModels());

  const [selectedModel, setSelectedModel] = useState<Model | undefined>();

  useEffect(() => {
    const savedModelId = localStorage.getItem('selectedModel');
    const defaultModel = models.find(m => m.id === savedModelId) || models[0];
    setSelectedModel(defaultModel);
  }, [models]);

  const selectModel = (modelId: string) => {
    const model = models.find(m => m.id === modelId);
    if (model) {
      setSelectedModel(model);
      localStorage.setItem('selectedModel', modelId);
    }
  };

  return {
    models,
    selectedModel,
    selectModel
  };
};