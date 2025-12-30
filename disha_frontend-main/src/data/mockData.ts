import { Marker } from '../types';

export const mockHospitals: Marker[] = [
  {
    id: 'h1',
    lat: 19.08,
    lon: 72.88,
    type: 'hospital',
    name: 'City General Hospital',
  },
  {
    id: 'h2',
    lat: 19.07,
    lon: 72.87,
    type: 'hospital',
    name: 'Emergency Medical Center',
  },
  {
    id: 'h3',
    lat: 19.085,
    lon: 72.875,
    type: 'hospital',
    name: 'Central Hospital',
  },
];

export const mockShelters: Marker[] = [
  {
    id: 's1',
    lat: 19.09,
    lon: 72.89,
    type: 'shelter',
    name: 'Community Shelter A',
  },
  {
    id: 's2',
    lat: 19.065,
    lon: 72.865,
    type: 'shelter',
    name: 'Emergency Bunker B',
  },
  {
    id: 's3',
    lat: 19.095,
    lon: 72.87,
    type: 'shelter',
    name: 'Safe Zone C',
  },
];

export const mockDisasterInfo = {
  type: 'Earthquake',
  severity: 'critical',
  affectedRadius: 5,
  description: 'Major seismic activity detected in your area',
};

export const mockSafetyRecommendations = [
  {
    category: 'Immediate Actions',
    items: [
      'Drop, Cover, and Hold On immediately',
      'Stay away from windows and heavy furniture',
      'If outdoors, move to an open area away from buildings',
      'Do not use elevators',
    ],
  },
  {
    category: 'What to Grab',
    items: [
      'Emergency kit with water and non-perishable food',
      'First aid supplies and medications',
      'Important documents (ID, insurance)',
      'Flashlight and portable phone charger',
      'Warm clothing and blankets',
    ],
  },
  {
    category: 'Emergency Contacts',
    items: [
      'Emergency Services: 911',
      'Disaster Helpline: 1-800-HELP-NOW',
      'Local Emergency Management: (555) 123-4567',
      'Red Cross Hotline: 1-800-RED-CROSS',
    ],
  },
];
