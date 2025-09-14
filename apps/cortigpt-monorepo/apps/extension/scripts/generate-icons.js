import iconGen from 'icon-gen';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// This will generate the exact sizes you need for your browser extension
const options = {
  favicon: {
    name: 'cortigpt-', // This will create cortigpt-16.png, cortigpt-24.png, etc.
    pngSizes: [16, 24, 32, 48, 64, 96, 128, 256] // All the sizes you need
  }
};

// Your source image
const sourceImage = path.join(__dirname, '../public/cortigpt-4.png');
// Output directory
const outputDir = path.join(__dirname, '../public');

iconGen(sourceImage, outputDir, options)
  .then((results) => {
    console.log('✅ Icons generated successfully!');
    console.log('Generated files:', results);
  })
  .catch((err) => {
    console.error('❌ Error generating icons:', err);
  });
