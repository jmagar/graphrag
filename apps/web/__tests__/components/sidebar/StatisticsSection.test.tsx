import { render, screen } from '@testing-library/react';
import { StatisticsSection } from '@/components/sidebar/StatisticsSection';

// Mock fetch
global.fetch = jest.fn();

describe('StatisticsSection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<StatisticsSection />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders statistics section header', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<StatisticsSection />);
    
    expect(screen.getByText('Statistics')).toBeInTheDocument();
  });
});
