import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const NotFound = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-6 max-w-md mx-auto">
        <div className="space-y-2">
          <h1 className="text-8xl font-bold gradient-text">404</h1>
          <h2 className="text-2xl font-semibold">Page Not Found</h2>
          <p className="text-muted-foreground">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </div>
        
        <div className="space-y-3">
          <Link to="/">
            <Button className="bg-gradient-primary hover:shadow-glow">
              Return Home
            </Button>
          </Link>
          <p className="text-sm text-muted-foreground">
            or go back to the{" "}
            <Link to="/dashboard" className="text-primary hover:underline">
              Dashboard
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
