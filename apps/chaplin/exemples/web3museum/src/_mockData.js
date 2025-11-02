// src/_mockData.js

// Use uma imagem de placeholder qualquer. Pode ser a home.png ou outra que você tenha.
import placeholderImage from './assets/home.png'; 

export const mockState = {
  finalResult: {
    "image_prompt": "A dramatic, high-contrast image set in an 18th-century Spanish Plaza de Toros (Maestranza architectural style). A medium, slightly elevated shot captures the final tercio de muerte...",
    "museum_label": "The Corrida de Toros was codified in 18th-century Spain, transitioning the event from noble custom to a professional public spectacle. This matador's heavy Traje de Luces highlights the celebrity status within a strictly regulated ritual, structured in three fixed acts (tercios)..."
  },
  // Use a URL da imagem gerada se tiver, ou um placeholder.
  // A URL.createObjectURL() é temporária, então é melhor usar uma URL estática para o mock.
  generatedImageUrl: 'https://i.imgur.com/fMlTOPQ.jpeg', 
  originalInput: "Corrida de Toros",
  isProcessing: false, // O processamento já terminou
};