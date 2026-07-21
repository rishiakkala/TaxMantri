import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { TaxRegimeComparison } from './TaxRegimeComparison';

describe('TaxRegimeComparison', () => {
  test('renders without crashing', () => {
    const { getByText } = render(<TaxRegimeComparison oldRegime={{}} newRegime={{}} onDownload={jest.fn()} />);
    expect(getByText(/Tax Regime Comparison/i)).toBeInTheDocument();
  });

  test('displays old and new regime data correctly', () => {
    const { getByText } = render(<TaxRegimeComparison oldRegime={{ Income: 5000 }} newRegime={{ Income: 6000 }} onDownload={jest.fn()} />);
    expect(getByText(/Income/i)).toBeInTheDocument();
    expect(getByText(/5000/i)).toBeInTheDocument();
    expect(getByText(/6000/i)).toBeInTheDocument();
  });

  test('calls onDownload when button is clicked', () => {
    const mockOnDownload = jest.fn();
    const { getByText } = render(<TaxRegimeComparison oldRegime={{}} newRegime={{}} onDownload={mockOnDownload} />);
    fireEvent.click(getByText(/Download PDF/i));
    expect(mockOnDownload).toHaveBeenCalled();
  });
});