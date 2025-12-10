"use client"

import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useEnvironment } from "@/contexts/environment-context";
import { Server, Globe, Zap } from "lucide-react";

export function EnvironmentToggle() {
  const { environment, setEnvironment } = useEnvironment();

  const handleToggle = (checked: boolean) => {
    const newEnv = checked ? 'devnet6' : 'testnet';
    setEnvironment(newEnv);
  };

  const envConfig = environment === 'testnet' 
    ? {
        icon: Globe,
        name: 'Testnet0',
        session: 'Session Testnet0',
        color: 'bg-blue-500/10 text-blue-600 border-blue-200',
        description: 'Stable testing environment (Testnet0)'
      }
  : {
        icon: Zap,
        name: 'Devnet-7',
        session: 'Session 11/22',
        color: 'bg-orange-500/10 text-orange-600 border-orange-200',
        description: 'Development environment'
      };

  const IconComponent = envConfig.icon;

  return (
    <div className="flex flex-col space-y-2 p-4 bg-muted/20 rounded-lg border">
      {/* Header dengan toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Server className="h-4 w-4 text-muted-foreground" />
          <Label htmlFor="environment-toggle" className="text-sm font-medium">
            Network Environment
          </Label>
        </div>
        <Switch
          id="environment-toggle"
          checked={environment === 'devnet6'}
          onCheckedChange={handleToggle}
        />
      </div>
      
      {/* Environment Info Card */}
      <div className={`flex items-center space-x-3 p-3 rounded-md border ${envConfig.color}`}>
        <IconComponent className="h-5 w-5" />
        <div className="flex-1 space-y-1">
          <div className="flex items-center space-x-2">
            <Badge 
              variant={environment === 'testnet' ? 'default' : 'secondary'}
              className="text-xs font-medium"
            >
              {envConfig.name}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {envConfig.session}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {envConfig.description}
          </p>
        </div>
      </div>
      
      {/* Status indicator */}
      <div className="flex items-center space-x-2 text-xs text-muted-foreground">
        <div className="flex items-center space-x-1">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>Connected</span>
        </div>
        <span>•</span>
        <span>Real-time switching enabled</span>
      </div>
    </div>
  );
}
