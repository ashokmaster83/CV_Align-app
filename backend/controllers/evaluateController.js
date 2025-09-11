import axios from 'axios';
import pdfParse from 'pdf-parse';
import { Job } from '../models/jobSchema.js';
import { spawnSync } from 'child_process';

function extractSkillsKG(text) {
  const result = spawnSync('python', [
    'c:/Users/Ashok/My_Intern/CVALIGN/CV_Align/extract_skills.py',
    text
  ], { encoding: 'utf-8' });
  if (result.error) throw result.error;
  try {
    const output = JSON.parse(result.stdout);
    return output.skills || [];
  } catch (e) {
    return [];
  }
}

async function callLlama(context) {
  // Example: POST to LLaMA API
  // const response = await axios.post('http://llama-api/evaluate', { context });
  // return response.data;
  return {
    analysis: `Match Score: 72%\nMissing Skills: Docker, Azure\nStrengths: Python, SQL\nRecommendation: Take a Docker fundamentals course.`
  };
}

export async function evaluateCV(req, res, next) {
  try {
    const { resumeUrl, jobId } = req.body;
    if (!resumeUrl || !jobId) {
      return res.status(400).json({ error: 'Missing resumeUrl or jobId' });
    }

  // 1. Download and extract text from resume PDF
  const pdfResponse = await axios.get(resumeUrl, { responseType: 'arraybuffer' });
  const buffer = Buffer.from(pdfResponse.data);
  const pdfData = await pdfParse(buffer);
  const resumeText = pdfData.text;

    // 2. Get JD from MongoDB
    const job = await Job.findById(jobId);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }
    const jdText = job.description || '';

    // 3. Extract skills/entities using KG Python script
    const resumeSkills = extractSkillsKG(resumeText);
    const jdSkills = extractSkillsKG(jdText);

    // 4. Compare skills
    const matchedSkills = resumeSkills.filter(skill => jdSkills.includes(skill));
    const missingSkills = jdSkills.filter(skill => !resumeSkills.includes(skill));

    // 5. Build RAG context
    const context = `Resume Summary: ${resumeText.slice(0, 500)}...\nJD Requirements: ${jdText.slice(0, 500)}...\nMatched Skills: ${matchedSkills.join(', ')}\nMissing Skills: ${missingSkills.join(', ')}`;

    // 6. Pass context to LLaMA
    const llamaResult = await callLlama(context);

    // 7. Return analysis
    res.json({ analysis: llamaResult.analysis });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
}