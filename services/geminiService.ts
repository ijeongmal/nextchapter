import { GoogleGenAI, Type, Schema } from "@google/genai";
import { SYSTEM_INSTRUCTION } from "../constants";
import { AnalysisResponse, GraphData, NodeType, BookNode, BookLink } from "../types";

export const analyzeBooks = async (book1: string, book2: string, book3: string): Promise<GraphData> => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API Key is missing. Please select a valid API Key.");
  }

  const ai = new GoogleGenAI({ apiKey });

  const responseSchema: Schema = {
    type: Type.OBJECT,
    properties: {
      nodes: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            id: { type: Type.STRING, description: "Unique book title" },
            title: { type: Type.STRING },
            author: { type: Type.STRING },
            type: { type: Type.STRING, enum: ["SEED", "RECOMMENDED"] },
            originSeedIndex: { type: Type.INTEGER, description: "0 for first seed, 1 for second, 2 for third" },
            description: { type: Type.STRING, description: "Short description in Korean" },
          },
          required: ["id", "title", "author", "type", "originSeedIndex", "description"],
        },
      },
      links: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            source: { type: Type.STRING, description: "id of source book" },
            target: { type: Type.STRING, description: "id of target book" },
            label: { type: Type.STRING, description: "Reason for connection in Korean (e.g. 'Dry Wit')" },
          },
          required: ["source", "target", "label"],
        },
      },
    },
    required: ["nodes", "links"],
  };

  const prompt = `
    Analyze these three books:
    1. ${book1}
    2. ${book2}
    3. ${book3}

    Generate a recommendation network graph.
    Ensure descriptions and link labels are in Korean.
  `;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
        responseMimeType: "application/json",
        responseSchema: responseSchema,
        temperature: 0.5, // Balance creativity with structured adherence
      },
    });

    const rawData = response.text ? JSON.parse(response.text) as AnalysisResponse : null;

    if (!rawData) {
      throw new Error("Failed to parse analysis result.");
    }

    // Transform to internal GraphData format
    const nodes: BookNode[] = rawData.nodes.map((n) => ({
      id: n.id,
      label: n.title,
      author: n.author,
      type: n.type === 'SEED' ? NodeType.SEED : NodeType.RECOMMENDED,
      group: n.originSeedIndex,
      description: n.description,
    }));

    const links: BookLink[] = rawData.links.map((l) => ({
      source: l.source,
      target: l.target,
      relation: l.label,
    }));

    return { nodes, links };

  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    throw error;
  }
};
