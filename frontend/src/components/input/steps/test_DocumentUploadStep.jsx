import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { DocumentUploadStep } from './DocumentUploadStep';

describe('DocumentUploadStep', () => {
  test('renders without crashing', () => {
    const { getByText } = render(<DocumentUploadStep onNext={jest.fn()} onFileUpload={jest.fn()} />);
    expect(getByText(/Upload Tax Documents/i)).toBeInTheDocument();
  });

  test('shows error for non-PDF files', () => {
    const { getByText, getByLabelText } = render(<DocumentUploadStep onNext={jest.fn()} onFileUpload={jest.fn()} />);
    const fileInput = getByLabelText(/upload tax documents/i);
    fireEvent.change(fileInput, { target: { files: [{ name: 'test.txt' }] } });
    expect(getByText(/Only PDF files are allowed./i)).toBeInTheDocument();
  });

  test('calls onFileUpload with the uploaded file', () => {
    const mockOnFileUpload = jest.fn();
    const { getByLabelText } = render(<DocumentUploadStep onNext={jest.fn()} onFileUpload={mockOnFileUpload} />);
    const fileInput = getByLabelText(/upload tax documents/i);
    fireEvent.change(fileInput, { target: { files: [{ name: 'test.pdf' }] } });
    expect(mockOnFileUpload).toHaveBeenCalledWith(expect.any(File));
  });

  test('shows error if next is clicked without file', () => {
    const { getByText } = render(<DocumentUploadStep onNext={jest.fn()} onFileUpload={jest.fn()} />);
    fireEvent.click(getByText(/Next/i));
    expect(getByText(/Please upload a file before proceeding./i)).toBeInTheDocument();
  });

  test('calls onNext when next is clicked with a file', () => {
    const mockOnNext = jest.fn();
    const { getByText, getByLabelText } = render(<DocumentUploadStep onNext={mockOnNext} onFileUpload={jest.fn()} />);
    const fileInput = getByLabelText(/upload tax documents/i);
    fireEvent.change(fileInput, { target: { files: [{ name: 'test.pdf' }] } });
    fireEvent.click(getByText(/Next/i));
    expect(mockOnNext).toHaveBeenCalled();
  });
});