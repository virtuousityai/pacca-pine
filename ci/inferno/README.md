# Pacca PINE Inferno Testing Environment

This directory contains the Docker Compose configuration necessary to run the ONC Inferno Certification test suite against a Pacca PINE instance.

## Overview

Inferno is a testing tool developed by the Office of the National Coordinator (ONC) for Health Information Technology to verify compliance with healthcare interoperability standards, particularly FHIR APIs and related security requirements.

The setup in this directory allows you to:
- Run a Pacca PINE instance configured for testing
- Run the Inferno testing tools in the same Docker network
- Execute automated compliance tests against the Pacca PINE FHIR API

## Quick Start

To run the Inferno test suite against Pacca PINE:

```bash
./run.sh
```

This script will:
1. Start all necessary Docker containers defined in `compose.yml`
2. Configure the Pacca PINE instance for testing
3. Start the Inferno test suite services including:
   - The main Inferno application
   - Worker nodes for test processing
   - NGINX for the web interface
   - Redis for caching and messaging
   - HL7 validator service

## Architecture

This Docker Compose setup extends the Inferno test tools from the `onc-certification-g10-test-kit` directory while placing them in the same Docker network as the Pacca PINE service. This ensures:

- All services can communicate with each other using service names
- Volume mounts in the extended services are relative to the `onc-certification-g10-test-kit` directory
- Custom Pacca PINE configuration can be injected for testing purposes

## Services

- **mysql**: Database for Pacca PINE
- **openemr**: The Pacca PINE instance to be tested
- **inferno**: The main Inferno testing application
- **worker**: Processes test jobs from the queue
- **nginx**: Web server for the Inferno UI (available at http://localhost:8000)
- **redis**: Caching and message queue
- **hl7_validator_service**: Validates HL7 message formats

## Configuration

The Pacca PINE instance is configured with:
- Ports: 8080 (HTTP) and 8523 (HTTPS)
- Development mode enabled for testing
- Direct volume mounting of Pacca PINE source code

## Additional Resources

- [Pacca PINE FHIR Documentation](../../FHIR_README.md)
- [ONC Certification Information](https://www.healthit.gov/topic/certification-ehrs/certification-health-it)
