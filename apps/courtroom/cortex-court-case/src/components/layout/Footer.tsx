import { Link } from "react-router-dom";
import { Scale, Github, Twitter, MessageCircle, ExternalLink } from "lucide-react";

export const Footer = () => {
  const footerLinks = [
    {
      title: "Product",
      links: [
        { label: "Courtroom", href: "/courtroom" },
        { label: "Cases", href: "/cases" },
        { label: "Validators", href: "/validators" },
        { label: "Documentation", href: "/docs" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "API Reference", href: "/docs#api" },
        { label: "Whitepaper", href: "/docs#whitepaper" },
        { label: "GitHub", href: "https://github.com", external: true },
        { label: "Bug Bounty", href: "/docs#security" },
      ],
    },
    {
      title: "Community",
      links: [
        { label: "Discord", href: "https://discord.com", external: true },
        { label: "Twitter", href: "https://twitter.com", external: true },
        { label: "Blog", href: "/docs#blog" },
        { label: "Forum", href: "https://forum.example.com", external: true },
      ],
    },
  ];

  return (
    <footer className="border-t border-border bg-muted/30">
      <div className="container mx-auto px-6 py-12">
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand Section */}
          <div className="lg:col-span-2">
            <Link to="/" className="flex items-center gap-2 mb-4">
              <Scale className="w-7 h-7 text-primary" />
              <span className="font-semibold text-lg">
                <span className="text-primary">Cortensor</span>
                <span className="text-foreground"> Judge</span>
              </span>
            </Link>
            <p className="text-muted-foreground text-sm mb-6 max-w-sm">
              Decentralized dispute resolution and safety layer for AI agents. 
              Ensuring trust and accountability in AI inference networks.
            </p>
            <div className="flex items-center gap-3">
              {[
                { Icon: Twitter, href: "https://twitter.com" },
                { Icon: Github, href: "https://github.com" },
                { Icon: MessageCircle, href: "https://discord.com" },
              ].map(({ Icon, href }, index) => (
                <a
                  key={index}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-lg border border-border flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary/50 transition-colors"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Links Sections */}
          {footerLinks.map((section) => (
            <div key={section.title}>
              <h4 className="font-semibold text-foreground text-sm mb-4">{section.title}</h4>
              <ul className="space-y-2.5">
                {section.links.map((link) => (
                  <li key={link.label}>
                    {link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
                      >
                        {link.label}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <Link
                        to={link.href}
                        className="text-sm text-muted-foreground hover:text-primary transition-colors"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Section */}
        <div className="mt-12 pt-6 border-t border-border flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Cortensor Judge. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <Link to="/docs#privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
            <Link to="/docs#terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};