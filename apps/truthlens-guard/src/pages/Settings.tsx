import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { 
  User, 
  Key, 
  Bell, 
  Shield, 
  Palette, 
  Save, 
  Eye, 
  EyeOff,
  Moon,
  Sun,
  Github,
  Mail,
  Smartphone,
  Globe,
  Trash2
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/hooks/use-toast';

export default function Settings() {
  const { user, setUser, isDarkMode, toggleDarkMode } = useAppStore();
  const { toast } = useToast();
  
  // Profile settings
  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
    avatar: user?.avatar || ''
  });

  // API settings
  const [apiKey, setApiKey] = useState('sk-truthlens-••••••••••••••••');
  const [showApiKey, setShowApiKey] = useState(false);
  
  // Notification settings
  const [notifications, setNotifications] = useState({
    email: true,
    push: false,
    analysisComplete: true,
    weeklyReport: true,
    securityAlerts: true
  });

  // Privacy settings
  const [privacy, setPrivacy] = useState({
    autoDelete: true,
    anonymousAnalytics: false,
    shareImprovements: true
  });

  const handleSaveProfile = () => {
    setUser({
      ...user,
      ...profile
    });
    toast({
      title: "Profile updated",
      description: "Your profile settings have been saved successfully."
    });
  };

  const handleGenerateApiKey = () => {
    const newKey = 'sk-truthlens-' + Math.random().toString(36).substring(2, 15);
    setApiKey(newKey);
    toast({
      title: "New API key generated",
      description: "Your new API key has been created. Please save it securely."
    });
  };

  const handleDeleteAccount = () => {
    // In a real app, this would show a confirmation dialog
    toast({
      title: "Account deletion",
      description: "This feature requires additional confirmation.",
      variant: "destructive"
    });
  };

  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2"
      >
        <h1 className="text-3xl font-bold gradient-text">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account preferences and application settings.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Settings Navigation */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-1"
        >
          <Card className="neumorphic border-0 sticky top-6">
            <CardHeader>
              <CardTitle className="text-lg">Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <a href="#profile" className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 text-sm">
                <User className="h-4 w-4" />
                Profile
              </a>
              <a href="#api" className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 text-sm">
                <Key className="h-4 w-4" />
                API Keys
              </a>
              <a href="#notifications" className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 text-sm">
                <Bell className="h-4 w-4" />
                Notifications
              </a>
              <a href="#privacy" className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 text-sm">
                <Shield className="h-4 w-4" />
                Privacy
              </a>
              <a href="#appearance" className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 text-sm">
                <Palette className="h-4 w-4" />
                Appearance
              </a>
            </CardContent>
          </Card>
        </motion.div>

        {/* Settings Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Profile Settings */}
          <motion.section
            id="profile"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="neumorphic border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Profile Information
                </CardTitle>
                <CardDescription>
                  Update your personal information and profile settings.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      value={profile.name}
                      onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                      placeholder="Enter your name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      placeholder="Enter your email"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="avatar">Avatar URL</Label>
                  <Input
                    id="avatar"
                    value={profile.avatar}
                    onChange={(e) => setProfile({ ...profile, avatar: e.target.value })}
                    placeholder="https://example.com/avatar.jpg"
                  />
                </div>

                <div className="flex justify-end">
                  <Button onClick={handleSaveProfile} className="bg-gradient-primary hover:shadow-glow">
                    <Save className="mr-2 h-4 w-4" />
                    Save Profile
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.section>

          {/* API Keys */}
          <motion.section
            id="api"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="neumorphic border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  API Keys
                </CardTitle>
                <CardDescription>
                  Manage your API keys for programmatic access to TruthLens.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="api-key">Current API Key</Label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        id="api-key"
                        type={showApiKey ? 'text' : 'password'}
                        value={apiKey}
                        readOnly
                        className="pr-10"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                    <Button variant="outline" onClick={handleGenerateApiKey}>
                      Generate New
                    </Button>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-muted/30 space-y-2">
                  <h4 className="font-medium text-sm">Usage Statistics</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Requests this month</p>
                      <p className="font-semibold">1,247 / 5,000</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Plan</p>
                      <Badge variant="secondary">Professional</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.section>

          {/* Notifications */}
          <motion.section
            id="notifications"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="neumorphic border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Notifications
                </CardTitle>
                <CardDescription>
                  Configure how you receive updates and alerts.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="email-notifications">Email Notifications</Label>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Receive updates via email
                      </p>
                    </div>
                    <Switch
                      id="email-notifications"
                      checked={notifications.email}
                      onCheckedChange={(checked) => 
                        setNotifications({ ...notifications, email: checked })
                      }
                    />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Smartphone className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="push-notifications">Push Notifications</Label>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Browser push notifications
                      </p>
                    </div>
                    <Switch
                      id="push-notifications"
                      checked={notifications.push}
                      onCheckedChange={(checked) => 
                        setNotifications({ ...notifications, push: checked })
                      }
                    />
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <Label className="text-sm font-medium">Notification Types</Label>
                    
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="analysis-complete" className="text-sm font-normal">
                          Analysis Complete
                        </Label>
                        <Switch
                          id="analysis-complete"
                          checked={notifications.analysisComplete}
                          onCheckedChange={(checked) => 
                            setNotifications({ ...notifications, analysisComplete: checked })
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <Label htmlFor="weekly-report" className="text-sm font-normal">
                          Weekly Reports
                        </Label>
                        <Switch
                          id="weekly-report"
                          checked={notifications.weeklyReport}
                          onCheckedChange={(checked) => 
                            setNotifications({ ...notifications, weeklyReport: checked })
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <Label htmlFor="security-alerts" className="text-sm font-normal">
                          Security Alerts
                        </Label>
                        <Switch
                          id="security-alerts"
                          checked={notifications.securityAlerts}
                          onCheckedChange={(checked) => 
                            setNotifications({ ...notifications, securityAlerts: checked })
                          }
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.section>

          {/* Privacy & Security */}
          <motion.section
            id="privacy"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="neumorphic border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Privacy & Security
                </CardTitle>
                <CardDescription>
                  Control your data privacy and security settings.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="auto-delete">Auto-delete Files</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically delete uploaded files after 30 days
                    </p>
                  </div>
                  <Switch
                    id="auto-delete"
                    checked={privacy.autoDelete}
                    onCheckedChange={(checked) => 
                      setPrivacy({ ...privacy, autoDelete: checked })
                    }
                  />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="anonymous-analytics">Anonymous Analytics</Label>
                    <p className="text-sm text-muted-foreground">
                      Help improve TruthLens with anonymous usage data
                    </p>
                  </div>
                  <Switch
                    id="anonymous-analytics"
                    checked={privacy.anonymousAnalytics}
                    onCheckedChange={(checked) => 
                      setPrivacy({ ...privacy, anonymousAnalytics: checked })
                    }
                  />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="share-improvements">Share for AI Improvements</Label>
                    <p className="text-sm text-muted-foreground">
                      Help train our AI models with anonymized data
                    </p>
                  </div>
                  <Switch
                    id="share-improvements"
                    checked={privacy.shareImprovements}
                    onCheckedChange={(checked) => 
                      setPrivacy({ ...privacy, shareImprovements: checked })
                    }
                  />
                </div>
              </CardContent>
            </Card>
          </motion.section>

          {/* Appearance */}
          <motion.section
            id="appearance"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card className="neumorphic border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  Appearance
                </CardTitle>
                <CardDescription>
                  Customize the look and feel of TruthLens.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      {isDarkMode ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                      <Label htmlFor="dark-mode">Dark Mode</Label>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Switch between light and dark themes
                    </p>
                  </div>
                  <Switch
                    id="dark-mode"
                    checked={isDarkMode}
                    onCheckedChange={toggleDarkMode}
                  />
                </div>
              </CardContent>
            </Card>
          </motion.section>

          {/* Danger Zone */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card className="neumorphic border-0 border-destructive/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-destructive">
                  <Trash2 className="h-5 w-5" />
                  Danger Zone
                </CardTitle>
                <CardDescription>
                  Irreversible and destructive actions.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 border border-destructive/20 rounded-lg">
                    <h4 className="font-medium mb-2">Delete Account</h4>
                    <p className="text-sm text-muted-foreground mb-4">
                      Permanently delete your account and all associated data. This action cannot be undone.
                    </p>
                    <Button 
                      variant="destructive" 
                      onClick={handleDeleteAccount}
                      className="w-full sm:w-auto"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete Account
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.section>
        </div>
      </div>
    </div>
  );
}