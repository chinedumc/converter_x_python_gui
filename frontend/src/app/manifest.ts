import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Excel2XML Converter',
    short_name: 'Excel2XML',
    description: 'Convert Excel files to XML with custom headers.',
    start_url: '/',
    display: 'standalone',
    background_color: '#F0F0F0',
    theme_color: '#8B0029',
    // icons are omitted as per generation constraints
  };
}
