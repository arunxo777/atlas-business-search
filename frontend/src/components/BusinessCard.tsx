import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  Star,
  AlertTriangle,
  Globe,
  Facebook,
  Linkedin,
  Link2,
  Award,
} from "lucide-react";
import type { BusinessRecord } from "@/api/client";
import { VerificationBadge } from "./VerificationBadge";

interface BusinessCardProps {
  business: BusinessRecord;
  defaultExpanded?: boolean;
}

export function BusinessCard({
  business,
  defaultExpanded = false,
}: BusinessCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showHours, setShowHours] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const hasConflicts = business.verification_status === "conflicted";
  const mapsUrl = business.address
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(business.address)}`
    : null;

  const content = (
    <div className="p-5 sm:p-6 space-y-4">
      {hasConflicts && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Conflicting values detected across sources
        </div>
      )}

      {business.image_urls.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {business.image_urls.slice(0, 4).map((img) => (
            <img
              key={img}
              src={img}
              alt={business.business_name}
              className="h-20 w-28 rounded-xl object-cover border border-white/10 shrink-0"
              loading="lazy"
            />
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {business.address && (
          <InfoRow icon={MapPin} label="Address">
            {mapsUrl ? (
              <a
                href={mapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline text-sm"
              >
                {business.address}
              </a>
            ) : (
              <span className="text-sm">{business.address}</span>
            )}
          </InfoRow>
        )}

        {business.phone.length > 0 && (
          <InfoRow icon={Phone} label="Phone">
            <div className="flex flex-wrap gap-2">
              {business.phone.map((p) => (
                <a
                  key={p}
                  href={`tel:${p}`}
                  className="text-sm font-mono text-primary hover:underline"
                >
                  {p}
                </a>
              ))}
            </div>
          </InfoRow>
        )}

        {business.email.length > 0 && (
          <InfoRow icon={Mail} label="Email">
            <div className="flex flex-wrap gap-2">
              {business.email.map((e) => (
                <a
                  key={e}
                  href={`mailto:${e}`}
                  className="text-sm text-primary hover:underline"
                >
                  {e}
                </a>
              ))}
            </div>
          </InfoRow>
        )}

        {business.website && (
          <InfoRow icon={Globe} label="Website">
            <a
              href={business.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline inline-flex items-center gap-1"
            >
              {business.website}
              <ExternalLink className="h-3 w-3" />
            </a>
          </InfoRow>
        )}

        {business.rating != null && (
          <InfoRow icon={Star} label="Rating">
            <span className="text-sm inline-flex items-center gap-1.5">
              <Star className="h-4 w-4 text-amber-400 fill-amber-400" />
              <span className="font-semibold">{business.rating.toFixed(1)}</span>
              {business.review_count != null && (
                <span className="text-muted-foreground">
                  ({business.review_count} reviews)
                </span>
              )}
            </span>
          </InfoRow>
        )}
      </div>

      {business.working_hours && Object.keys(business.working_hours).length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowHours(!showHours)}
            className="text-xs font-semibold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
          >
            Working Hours {showHours ? "▲" : "▼"}
          </button>
          {showHours && (
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-1 text-sm pl-1">
              {Object.entries(business.working_hours).map(([day, hours]) => (
                <div key={day} className="flex gap-2 py-0.5">
                  <span className="font-medium w-24 text-muted-foreground">{day}</span>
                  <span>{hours}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(business.services.length > 0 || business.specialties.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {[...business.services, ...business.specialties].map((tag) => (
            <span
              key={tag}
              className="px-2.5 py-0.5 rounded-full border border-white/10 bg-white/[0.04] text-xs text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {business.license_information && (
        <p className="text-sm">
          <span className="text-muted-foreground">License: </span>
          {business.license_information}
        </p>
      )}

      {(business.certifications.length > 0 || business.awards.length > 0) && (
        <div className="flex flex-wrap gap-4 text-sm">
          {business.certifications.length > 0 && (
            <p>
              <Award className="inline h-3.5 w-3.5 mr-1 text-muted-foreground" />
              {business.certifications.join(", ")}
            </p>
          )}
          {business.awards.length > 0 && (
            <p className="text-muted-foreground">{business.awards.join(", ")}</p>
          )}
        </div>
      )}

      {Object.keys(business.social_profiles).length > 0 && (
        <div className="flex gap-3">
          {business.social_profiles.facebook && (
            <a
              href={business.social_profiles.facebook}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:opacity-80 transition-opacity"
            >
              <Facebook className="h-5 w-5" />
            </a>
          )}
          {business.social_profiles.linkedin && (
            <a
              href={business.social_profiles.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:opacity-80 transition-opacity"
            >
              <Linkedin className="h-5 w-5" />
            </a>
          )}
        </div>
      )}

      {Object.keys(business.source_urls).length > 0 && (
        <div className="border-t border-white/[0.06] pt-4">
          <button
            type="button"
            onClick={() => setShowSources(!showSources)}
            className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
          >
            <Link2 className="h-3.5 w-3.5" />
            Source Proof ({business.raw_sources.length}) {showSources ? "▲" : "▼"}
          </button>
          {showSources && (
            <div className="mt-3 space-y-3 text-xs">
              {Object.entries(
                (business.verification_details?.field_source_recommendations as Record<
                  string,
                  { recommended_source?: string; url?: string }
                >) || {}
              ).length > 0 && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-3">
                  <p className="font-semibold text-primary mb-2">Recommended sources</p>
                  {Object.entries(
                    business.verification_details
                      .field_source_recommendations as Record<
                      string,
                      { recommended_source?: string; url?: string }
                    >
                  ).map(([field, rec]) => (
                    <div key={field} className="flex gap-2 py-0.5">
                      <span className="capitalize w-24 shrink-0 text-muted-foreground">
                        {field}:
                      </span>
                      <span className="font-medium">{rec.recommended_source}</span>
                    </div>
                  ))}
                </div>
              )}
              {Object.entries(business.source_urls).map(([field, urls]) => (
                <div key={field}>
                  <span className="font-medium capitalize text-muted-foreground">
                    {field}
                  </span>
                  <div className="mt-1 space-y-0.5">
                    {urls.map((url) => (
                      <a
                        key={url}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-primary hover:underline truncate font-mono text-[11px]"
                      >
                        {url}
                      </a>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
        <span className="text-xs text-muted-foreground">
          Reliability:{" "}
          <span className="font-mono font-medium text-foreground">
            {(business.source_reliability_score * 100).toFixed(0)}%
          </span>
        </span>
        {business.rank_score != null && business.rank_score > 0 && (
          <span className="text-xs font-mono text-primary">
            Score: {business.rank_score.toFixed(1)}
          </span>
        )}
      </div>
    </div>
  );

  if (defaultExpanded) {
    return content;
  }

  return (
    <div className="rounded-2xl glass overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/[0.03] transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          {business.rank_score != null && business.rank_score > 0 && (
            <span className="shrink-0 rounded-lg bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 px-2.5 py-1 text-xs font-bold font-mono text-violet-300">
              {business.rank_score.toFixed(1)}
            </span>
          )}
          <h3 className="font-semibold truncate">{business.business_name}</h3>
          <VerificationBadge status={business.verification_status} />
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
      </button>
      {expanded && content}
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof MapPin;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.04]">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-0.5">
          {label}
        </p>
        {children}
      </div>
    </div>
  );
}
