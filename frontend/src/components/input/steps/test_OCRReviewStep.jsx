import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { OCRReviewStep } from './OCRReviewStep';

describe('OCRReviewStep', () => {
  test('renders without crashing', () => {
    const { getByText } = render(<OCRReviewStep ocrData={{}} onUpdate={jest.fn()} onNext={jest.fn()} />);
    expect(getByText(/Review and Correct OCR Data/i)).toBeInTheDocument();
  });

  test('shows error if fields are incomplete', () => {
    const { getByText } = render(<OCRReviewStep ocrData={{ Income: '', TaxPaid: '' }} onUpdate={jest.fn()} onNext={jest.fn()} />);
    fireEvent.click(getByText(/Next/i));
    expect(getByText(/Please complete all fields before proceeding./i)).toBeInTheDocument();
  });

  test('calls onUpdate with updated OCR data', () => {
    const mockOnUpdate = jest.fn();
    const { getByLabelText } = render(<OCRReviewStep ocrData={{ Income: '' }} onUpdate={mockOnUpdate} onNext={jest.fn()} />);
    fireEvent.change(getByLabelText(/Income/i), { target: { value: '5000' } });
    expect(mockOnUpdate).toHaveBeenCalledWith({ Income: '5000' });
  });

  test('calls onNext when all fields are filled', () => {
    const mockOnNext = jest.fn();
    const { getByLabelText, getByText } = render(<OCRReviewStep ocrData={{ Income: '5000', TaxPaid: '500' }} onUpdate={jest.fn()} onNext={mockOnNext} />);
    fireEvent.click(getByText(/Next/i));
    expect(mockOnNext).toHaveBeenCalled();
  });
});