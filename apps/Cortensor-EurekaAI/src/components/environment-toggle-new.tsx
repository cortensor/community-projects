"use client"

import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useEnvironment } from "@/contexts/environment-context";

export function EnvironmentToggle() {
  const { environment, setEnvironment } = useEnvironment();

    const handleToggle = () => {
    const newEnv = environment === 'testnet' ? 'devnet6' : 'testnet'
    setEnvironment(newEnv)
  }

  return (
    <div className="flex items-center space-x-3 p-3 bg-muted/30 rounded-lg border">
      <div className="flex items-center space-x-2">
        <Switch
          id="environment-toggle"
          checked={environment === 'devnet6'}
          onCheckedChange={handleToggle}
        />
        <Label htmlFor="environment-toggle" className="text-sm font-medium">
          Environment
        </Label>
      </div>
      
      <div className="flex items-center space-x-2">
        <Badge 
          variant={environment === 'testnet' ? 'default' : 'outline'}
          className="text-xs"
        >
          {environment === 'testnet' ? 'L3 Testnet' : 'Devnet6'}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {environment === 'testnet' 
            ? '205.209.119.106:5010' 
            : '173.214.163.250:5010'
          }
        </span>
      </div>
    </div>
  );
}
