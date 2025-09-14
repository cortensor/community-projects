"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { 
  NavigationMenu, 
  NavigationMenuContent, 
  NavigationMenuItem, 
  NavigationMenuLink, 
  NavigationMenuList, 
  NavigationMenuTrigger 
} from "@/components/ui/navigation-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu, X, Zap, Users, Lightbulb, ChevronDown } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { ConnectWalletButton } from '@/components/ui/connect-wallet-button';

// Type definitions
interface NavigationSubItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavigationItemWithDropdown {
  title: string;
  items: NavigationSubItem[];
}

interface NavigationItemSimple {
  name: string;
  href: string;
}

type NavigationItem = NavigationItemWithDropdown | NavigationItemSimple;

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const isMobile = useIsMobile();

  const navigationItems = [
    {
      title: "Features",
      items: [
        { name: "AI Agents", href: "#agents", icon: () => <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 h-4" /> },
        { name: "Neural Networks", href: "#neural", icon: Zap },
        { name: "Use Cases", href: "#use-cases", icon: Lightbulb }
      ]
    },
    { name: "How It Works", href: "#how-it-works" },
    { name: "About", href: "#about" },
    { name: "Contact", href: "#contact" }
  ];

  const MobileNavItem = ({ item }: { item: NavigationItem }) => {
    if ('items' in item) {
      return (
        <div className="space-y-2">
          <div className="font-medium text-foreground px-4 py-2">{item.title}</div>
          {item.items.map((subItem: NavigationSubItem) => (
            <a
              key={subItem.name}
              href={subItem.href}
              className="flex items-center space-x-3 px-6 py-2 text-muted-foreground hover:text-primary transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <subItem.icon className="h-4 w-4" />
              <span>{subItem.name}</span>
            </a>
          ))}
        </div>
      );
    }

    return (
      <a
        href={item.href}
        className="block px-4 py-2 text-foreground hover:text-primary transition-colors"
        onClick={() => setIsOpen(false)}
      >
        {item.name}
      </a>
    );
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo - smaller on mobile, stays on left */}
          <div className={`flex items-center ${
            isMobile ? 'space-x-2' : 'space-x-3'
          }`}>
            <div className={`bg-gradient-primary rounded-lg flex items-center justify-center ${
              isMobile ? 'w-6 h-6' : 'w-8 h-8'
            }`}>
              <img src="/cortigpt-4.png" alt="CortiGPT" className={`${
                isMobile ? 'h-4 w-4' : 'h-5 w-5'
              }`} />
            </div>
            <span className={`font-bold gradient-text ${
              isMobile ? 'text-sm' : 'text-xl'
            }`}>CortiGPT</span>
          </div>

          {/* Desktop Navigation */}
          {!isMobile && (
            <NavigationMenu className="hidden md:flex">
              <NavigationMenuList>
                {navigationItems.map((item) => (
                  <NavigationMenuItem key={item.title || item.name}>
                    {item.items ? (
                      <>
                        <NavigationMenuTrigger className="bg-transparent hover:bg-accent/10 data-[state=open]:bg-accent/10">
                          {item.title}
                        </NavigationMenuTrigger>
                        <NavigationMenuContent>
                          <div className="grid gap-3 p-6 w-80">
                            {item.items.map((subItem) => (
                              <NavigationMenuLink
                                key={subItem.name}
                                href={subItem.href}
                                className="flex items-center space-x-3 p-3 rounded-md hover:bg-accent/10 transition-colors group"
                              >
                                <div className="p-2 rounded-md bg-primary/10 group-hover:bg-primary/20 transition-colors">
                                  <subItem.icon className="h-4 w-4 text-primary" />
                                </div>
                                <div>
                                  <div className="font-medium text-foreground">{subItem.name}</div>
                                </div>
                              </NavigationMenuLink>
                            ))}
                          </div>
                        </NavigationMenuContent>
                      </>
                    ) : (
                      <NavigationMenuLink
                        href={item.href}
                        className="inline-flex h-10 w-max items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors hover:bg-accent/10 focus:bg-accent/10 focus:outline-none disabled:pointer-events-none disabled:opacity-50"
                      >
                        {item.name}
                      </NavigationMenuLink>
                    )}
                  </NavigationMenuItem>
                ))}
              </NavigationMenuList>
            </NavigationMenu>
          )}

          {/* Connect Wallet Button - Always visible but responsive */}
          <div className={`flex items-center gap-2 ml-auto ${
            isMobile ? 'ml-4' : 'ml-8'
          }`}>
            <ConnectWalletButton isMobile={isMobile} className="flex-shrink-0" />
            
            {/* Mobile Menu Button */}
            {isMobile && (
              <Sheet open={isOpen} onOpenChange={setIsOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="md:hidden ml-2 flex-shrink-0">
                    <Menu className="h-5 w-5" />
                    <span className="sr-only">Toggle menu</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-80 bg-background/95 backdrop-blur-lg border-border/20">
                  <div className="flex flex-col h-full">
                    {/* Mobile Header */}
                    <div className="flex items-center justify-between py-4 border-b border-border/20">
                      <div className="flex items-center space-x-2">
                        <div className="w-6 h-6 bg-gradient-primary rounded-md flex items-center justify-center">
                          <Zap className="h-4 w-4 text-primary-foreground" />
                        </div>
                        <span className="font-bold gradient-text">CortiGPT</span>
                      </div>
                    </div>

                    {/* Mobile Navigation */}
                    <div className="flex-1 py-6 space-y-2">
                      {navigationItems.map((item) => (
                        <MobileNavItem key={item.title || item.name} item={item} />
                      ))}
                    </div>

                    {/* Mobile Connect Wallet Button */}
                    <div className="border-t border-border/20 pt-6">
                      <ConnectWalletButton 
                        isMobile={true} 
                        onModalOpen={() => setIsOpen(false)} 
                      />
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;