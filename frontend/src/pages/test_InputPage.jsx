import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { InputPage } from './InputPage';

describe('InputPage', () => {
  test('renders DocumentUploadStep initially', () => {
    const { getByText } = render(<InputPage />);
    expect(getByText(/Upload Tax Documents/i)).toBeInTheDocument();
  });

  test('navigates to OCRReviewStep after file upload', () => {
    const { getByText, getByLabelText } = render(<InputPage />);
    const fileInput = getByLabelText(/upload tax documents/i);
    fireEvent.change(fileInput, { target: { files: [{ name: 'test.pdf' }] } });
    fireEvent.click(getByText(/Next/i));
    expect(getByText(/Review and Correct OCR Data/i)).toBeInTheDocument();
  });
});