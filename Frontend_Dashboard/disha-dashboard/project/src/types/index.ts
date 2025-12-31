export interface Disaster {
  id: string;
  type: DisasterType;
  latitude: number;
  longitude: number;
  radius_meters: number;
  timestamp: string;
}

export type DisasterType =
  | "Flood"
  | "Earthquake"
  | "Fire"
  | "Terrorist Attack"
  | "Cyclone"
  | "Tsunami"
  | "Landslide"
  | "Chemical Spill"
  | "Nuclear Incident"
  | "Volcanic Eruption"
  | "Heatwave"
  | "Biological Hazard";

export interface TriggerDisasterRequest {
  type: DisasterType;
  latitude: number;
  longitude: number;
  radius_meters: number;
}

export interface NewsItem {
  headline: string;
  type: string;
  locations: string[];
  summary: string;
  source: string;
  date: string;
}

export interface NewsResponse {
  disasters: NewsItem[];
}

export type ViewType = 'home' | 'trigger' | 'news' | 'developers';