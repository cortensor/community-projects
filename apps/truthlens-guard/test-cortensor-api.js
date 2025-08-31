// Test Cortensor API Connection
const axios = require('axios');

async function testCortensorAPI() {
  const client = axios.create({
    baseURL: 'http://localhost:5010',
    timeout: 30000,
    headers: {
      'Authorization': 'Bearer default-dev-token',
      'Content-Type': 'application/json',
      'User-Agent': 'TruthLens-Test/1.0.0'
    }
  });

  try {
    console.log('🔍 Testing Cortensor API connection...\n');

    // Test 1: Health check
    console.log('📊 Test 1: Health Check');
    const healthResponse = await client.get('/api/v1/status');
    console.log('✅ Health Status:', healthResponse.status);
    console.log('📄 Response:', JSON.stringify(healthResponse.data, null, 2));

    // Test 2: Submit fact-checking prompt
    console.log('\n🤖 Test 2: Fact-Checking Request');
    const factCheckPrompt = `FACT-CHECKING TASK: Analyze this claim: "The Earth is flat"
Provide your analysis in JSON format: {"score": 0.1, "reasoning": "Scientific evidence proves Earth is spherical", "sources": ["nasa.gov", "space.com"]}`;

    const inferenceRequest = {
      session_id: 0,
      prompt: factCheckPrompt,
      stream: false,
      timeout: 30
    };

    const response = await client.post('/api/v1/completions', inferenceRequest);
    console.log('✅ Inference Status:', response.status);
    console.log('📄 Response:', JSON.stringify(response.data, null, 2));

    console.log('\n🎉 Cortensor API Test Successful!');

  } catch (error) {
    console.error('❌ API Test Failed:');
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Data:', error.response.data);
    } else {
      console.error('Error:', error.message);
    }

    console.log('\n💡 Troubleshooting:');
    console.log('1. Make sure Cortensor Router Node is running on localhost:5010');
    console.log('2. Check if default-dev-token is accepted');
    console.log('3. Verify the API endpoints are correct');
  }
}

// Run the test
testCortensorAPI();
