import { defineConfig, type Config } from '@wagmi/cli'
import { react } from '@wagmi/cli/plugins'
import SessionV2ABI from './abis/SessionV2.json'
import SessionQueueV2ABI from './abis/SessionQueueV2.json'
import type { Abi } from 'viem'

export default defineConfig({
    out: 'src/generated.ts',
    contracts: [
        {
            name: 'SessionV2',
            address: {
                421614: '0x2f1380ba4eFBE866C811862e50923585b31EA03B',
            },
            abi: SessionV2ABI as Abi,
        },
        {
            name: 'SessionQueueV2',
            address: {
                421614: '0x2fCC55699048eD2e22fe46b1dD45557024fD1836',
            },
            abi: SessionQueueV2ABI as Abi,
        },
    ],
    plugins: [react()],
}) as Config