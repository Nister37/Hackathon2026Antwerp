import type { ReactNode } from 'react';
import { MoreVertical } from 'lucide-react';
import { Link } from 'react-router-dom';

type WidgetProps = {
  title: string;
  className?: string;
  destination?: string;
  children: ReactNode;
};

export function Widget({ title, className = '', destination, children }: WidgetProps) {
  const headingId = `widget-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;

  return (
    <section className={`widget ${className}`} aria-labelledby={headingId}>
      <div className="widget-header">
        <h2 id={headingId}>{title}</h2>
        {destination && (
          <details className="widget-menu">
            <summary aria-label={`More options for ${title}`}><MoreVertical size={21} /></summary>
            <div className="widget-menu-content"><Link to={destination}>View details</Link></div>
          </details>
        )}
      </div>
      <div className="widget-body">{children}</div>
    </section>
  );
}
