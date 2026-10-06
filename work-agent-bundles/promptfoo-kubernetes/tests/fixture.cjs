module.exports = class FixtureProvider {
  id() { return 'synthetic-offline-fixture'; }
  async callApi() { return {output:'SYNTHETIC_AKS_EVALUATION_OK'}; }
};
