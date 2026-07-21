import React from 'react';
import PropTypes from 'prop-types';
import { TaxRegimeComparison } from '../components/results/TaxRegimeComparison';

export const ResultsPage = ({ oldRegime, newRegime, onDownload }) => {
  return (
    <div className="container mx-auto p-4">
      <TaxRegimeComparison
        oldRegime={oldRegime}
        newRegime={newRegime}
        onDownload={onDownload}
      />
    </div>
  );
};

ResultsPage.propTypes = {
  oldRegime: PropTypes.object.isRequired,
  newRegime: PropTypes.object.isRequired,
  onDownload: PropTypes.func.isRequired,
};