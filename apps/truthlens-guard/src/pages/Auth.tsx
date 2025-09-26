import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { 
  Shield, 
  Github, 
  Mail, 
  Eye, 
  EyeOff, 
  ArrowLeft,
  Sparkles,
  Lock
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/hooks/use-toast';

type AuthMode = 'signin' | 'signup' | 'forgot';

export default function Auth() {
  const navigate = useNavigate();
  const { setUser } = useAppStore();
  const { toast } = useToast();
  
  const [mode, setMode] = useState<AuthMode>('signin');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Simulate authentication
    setTimeout(() => {
      if (mode === 'signin') {
        setUser({
          id: '1',
          name: 'Alex Johnson',
          email: form.email || 'alex@example.com',
          avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=64&h=64&fit=crop&crop=face'
        });
        
        toast({
          title: "Welcome back!",
          description: "You've successfully signed in to TruthLens."
        });
        
        navigate('/dashboard');
      } else if (mode === 'signup') {
        setUser({
          id: '1',
          name: form.name || 'New User',
          email: form.email,
          avatar: ''
        });
        
        toast({
          title: "Account created!",
          description: "Welcome to TruthLens. Your account has been created successfully."
        });
        
        navigate('/dashboard');
      } else {
        toast({
          title: "Reset link sent",
          description: "Check your email for password reset instructions."
        });
        setMode('signin');
      }
      
      setLoading(false);
    }, 1500);
  };

  const handleSocialLogin = (provider: string) => {
    toast({
      title: `${provider} login`,
      description: "Social authentication would be handled here."
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 mesh-bg opacity-20" />
      
      <div className="w-full max-w-md relative z-10">
        {/* Back Button */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="mb-6"
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/')}
            className="text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="neumorphic border-0 overflow-hidden">
            <CardHeader className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-gradient-primary flex items-center justify-center">
                <Shield className="h-8 w-8 text-primary-foreground" />
              </div>
              
              <div>
                <CardTitle className="text-2xl gradient-text">
                  {mode === 'signin' ? 'Welcome back' : 
                   mode === 'signup' ? 'Create account' : 'Reset password'}
                </CardTitle>
                <CardDescription className="mt-2">
                  {mode === 'signin' ? 'Sign in to your TruthLens account' :
                   mode === 'signup' ? 'Join TruthLens to start analyzing media' :
                   'Enter your email to reset your password'}
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Social Login */}
              {(mode === 'signin' || mode === 'signup') && (
                <div className="space-y-3">
                  <Button
                    variant="outline"
                    className="w-full h-11 glassmorphism hover:bg-muted/50"
                    onClick={() => handleSocialLogin('Google')}
                  >
                    <Mail className="mr-2 h-4 w-4" />
                    Continue with Google
                  </Button>
                  
                  <Button
                    variant="outline"
                    className="w-full h-11 glassmorphism hover:bg-muted/50"
                    onClick={() => handleSocialLogin('GitHub')}
                  >
                    <Github className="mr-2 h-4 w-4" />
                    Continue with GitHub
                  </Button>

                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <Separator className="w-full" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-background px-2 text-muted-foreground">
                        Or continue with
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'signup' && (
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      type="text"
                      placeholder="Enter your full name"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      required={mode === 'signup'}
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    required
                  />
                </div>

                {(mode === 'signin' || mode === 'signup') && (
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                        className="pr-10"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                )}

                {mode === 'signup' && (
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <Input
                      id="confirmPassword"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Confirm your password"
                      value={form.confirmPassword}
                      onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                      required
                    />
                  </div>
                )}

                {mode === 'signin' && (
                  <div className="flex items-center justify-between text-sm">
                    <span></span>
                    <button
                      type="button"
                      onClick={() => setMode('forgot')}
                      className="text-primary hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                <Button
                  type="submit"
                  className="w-full h-11 bg-gradient-primary hover:shadow-glow"
                  disabled={loading}
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-primary-foreground/20 border-t-primary-foreground rounded-full animate-spin" />
                      {mode === 'signin' ? 'Signing in...' : 
                       mode === 'signup' ? 'Creating account...' : 'Sending reset link...'}
                    </div>
                  ) : (
                    <>
                      {mode === 'signin' && <Lock className="mr-2 h-4 w-4" />}
                      {mode === 'signup' && <Sparkles className="mr-2 h-4 w-4" />}
                      {mode === 'forgot' && <Mail className="mr-2 h-4 w-4" />}
                      
                      {mode === 'signin' ? 'Sign In' :
                       mode === 'signup' ? 'Create Account' : 'Send Reset Link'}
                    </>
                  )}
                </Button>
              </form>

              {/* Toggle Mode */}
              <div className="text-center text-sm text-muted-foreground">
                {mode === 'signin' ? (
                  <div>
                    Don't have an account?{' '}
                    <button
                      onClick={() => setMode('signup')}
                      className="text-primary hover:underline font-medium"
                    >
                      Sign up
                    </button>
                  </div>
                ) : mode === 'signup' ? (
                  <div>
                    Already have an account?{' '}
                    <button
                      onClick={() => setMode('signin')}
                      className="text-primary hover:underline font-medium"
                    >
                      Sign in
                    </button>
                  </div>
                ) : (
                  <div>
                    Remember your password?{' '}
                    <button
                      onClick={() => setMode('signin')}
                      className="text-primary hover:underline font-medium"
                    >
                      Sign in
                    </button>
                  </div>
                )}
              </div>

              {/* Security Notice */}
              <div className="p-3 rounded-lg bg-muted/30 text-xs text-muted-foreground text-center">
                <Shield className="h-3 w-3 inline mr-1" />
                Your data is protected with enterprise-grade security
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8 text-center text-sm text-muted-foreground"
        >
          <p>Join 10,000+ professionals using TruthLens</p>
          <div className="flex justify-center gap-4 mt-2">
            <span>✓ 99.2% Accuracy</span>
            <span>✓ Instant Results</span>
            <span>✓ Privacy First</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}