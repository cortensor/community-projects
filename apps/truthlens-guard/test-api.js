#!/usr/bin/env node

/**
 * TruthLens API Test Script
 * Demonstrates Cortensor decentralized AI inference integration
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3001/api';

async function testTruthLensAPI() {
  console.log('🔍 TruthLens API Test - Cortensor Decentralized AI Integration\n');

  try {
    // Test 1: Health Check
    console.log('1. Testing API Health...');
    const healthResponse = await axios.get(`${API_BASE}/health`);
    console.log('✅ API Health:', healthResponse.data.message);
    
    // Test 2: Backend Status
    console.log('\n2. Checking Cortensor Network Status...');
    const statusResponse = await axios.get(`${API_BASE}/analysis/status`);
    const status = statusResponse.data.data;
    console.log('🌐 Cortensor Connected:', status.cortensorConnected);
    console.log('⚡ Available Miners:', status.availableMiners);
    console.log('🕒 Last Health Check:', status.lastHealthCheck);

    // Test 3: Fact-Check Analysis
    console.log('\n3. Testing Fact-Check Analysis...');
    const testClaims = [
      {
        claim: "Climate change is primarily caused by human activities according to scientific consensus",
        type: "text"
      },
      {
        claim: "Vaccines are effective at preventing infectious diseases",
        type: "text"
      },
      {
        claim: "The Earth is flat and space agencies are covering it up",
        type: "text"
      }
    ];

    for (let i = 0; i < testClaims.length; i++) {
      const testClaim = testClaims[i];
      console.log(`\n📋 Test ${i + 1}: "${testClaim.claim.substring(0, 50)}..."`);
      
      try {
        const analysisResponse = await axios.post(`${API_BASE}/analysis/analyze`, {
          claim: testClaim.claim,
          type: testClaim.type,
          options: {
            minMiners: 3,
            timeout: 30000
          }
        });

        const analysis = analysisResponse.data.data.analysis;
        console.log(`  🎯 Credibility Score: ${(analysis.credibilityScore * 100).toFixed(1)}%`);
        console.log(`  🔍 Confidence: ${(analysis.confidence * 100).toFixed(1)}%`);
        console.log(`  ✅ Is Credible: ${analysis.isCredible}`);
        console.log(`  👥 Miners Consulted: ${analysis.minerResponses.length}`);
        console.log(`  📚 Supporting Sources: ${analysis.supportingSources.length}`);
        
        // Show top miner reasoning
        if (analysis.minerResponses.length > 0) {
          const topMiner = analysis.minerResponses[0];
          console.log(`  🤖 Top Miner (${topMiner.minerId}): ${topMiner.reasoning.substring(0, 80)}...`);
        }

      } catch (error) {
        console.log(`  ❌ Analysis failed: ${error.response?.data?.error || error.message}`);
      }
    }

    console.log('\n🎉 TruthLens API Test Complete!');
    console.log('\n📍 Next Steps:');
    console.log('  • Open http://localhost:8080 to use the web interface');
    console.log('  • Try different claims to see Cortensor consensus in action');
    console.log('  • Check the History page to see detailed miner responses');
    console.log('  • Configure real Cortensor API key for production use');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    if (error.code === 'ECONNREFUSED') {
      console.log('\n💡 Make sure the backend server is running:');
      console.log('  cd backend && npm run dev');
    }
  }
}

// Run the test
testTruthLensAPI();
