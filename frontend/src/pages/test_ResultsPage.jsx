import React from 'react';
import { render } from '@testing-library/react';
import { ResultsPage } from './ResultsPage';

describe('ResultsPage', () => {
  test('renders TaxRegimeComparison component', () => {
    const { getByText } = render(<ResultsPage oldRegime={{}} newRegime={{}} onDownload={jest.fn()} />);
    expect(getByText(/Tax Regime Comparison/i)).toBeInTheDocument();
  });
});